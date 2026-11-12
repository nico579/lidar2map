"""Lecture bornée des ZIP officiels par HTTP Range, sans téléchargement global.

Prototype isolé : refus explicite si le serveur ignore Range, contrôle de la
taille, de l'identité HTTP et du CRC ZIP. Aucune modification des altitudes.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


class RangeUnsupported(IOError):
    pass


class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url, cache_dir, *, max_bytes=128 * 1024 * 1024):
        super().__init__()
        self.url = url
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.requested_bytes = 0
        self.position = 0
        self.size = None
        self.etag = None
        self.last_modified = None
        self.lock = threading.RLock()
        self.records = []
        self._tail = self._request("bytes=-65536", use_cache=False)
        self._tail_offset = self.size - len(self._tail)

    def _request(self, range_value, use_cache=True):
        key = hashlib.sha256((self.url + str(self.etag) + str(self.last_modified)
                              + range_value).encode()).hexdigest()
        path = self.cache_dir / (key + ".bin")
        meta_path = self.cache_dir / (key + ".json")
        if use_cache and path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() == meta["sha256"]:
                self.records.append(meta)
                return payload
        headers = {"User-Agent": "lidar2map-native-validation/1.0", "Range": range_value,
                   "Accept-Encoding": "identity"}
        if self.etag:
            headers["If-Match"] = self.etag
        with urlopen(Request(self.url, headers=headers), timeout=45) as response:
            if response.status != 206:
                raise RangeUnsupported(f"HTTP {response.status} : Range ignoré, téléchargement global refusé")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if not match:
                raise IOError("Content-Range manquant ou invalide")
            first, last, total = map(int, match.groups())
            length = last - first + 1
            if length <= 0 or length > 8 * 1024 * 1024 or self.requested_bytes + length > self.max_bytes:
                raise IOError("Budget de lecture HTTP Range dépassé")
            if self.size is not None and total != self.size:
                raise IOError("Taille de l'archive modifiée pendant la lecture")
            if range_value.startswith("bytes=-"):
                if last != total - 1 or length != min(int(range_value[7:]), total):
                    raise IOError("Réponse Range suffixe incohérente")
            else:
                expected = tuple(map(int, range_value[6:].split("-")))
                if (first, last) != expected:
                    raise IOError("Réponse Range déplacée/tronquée")
            etag = response.headers.get("ETag")
            modified = response.headers.get("Last-Modified")
            if self.size is not None and (etag != self.etag or modified != self.last_modified):
                raise IOError("Identité de l'archive modifiée pendant la lecture")
            self.size, self.etag, self.last_modified = total, etag, modified
            payload = response.read(length + 1)
            if len(payload) != length:
                raise IOError("Réponse Range de taille inattendue")
            self.requested_bytes += length
            metadata = {
                "url": self.url, "range": range_value, "status": 206,
                "content_range": response.headers["Content-Range"], "etag": etag,
                "last_modified": modified, "bytes": length,
                "date_utc": datetime.now(timezone.utc).isoformat(),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        path.write_bytes(payload)
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        self.records.append(metadata)
        return payload

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        position = offset if whence == io.SEEK_SET else self.position + offset if whence == io.SEEK_CUR else self.size + offset
        if position < 0 or position > self.size:
            raise ValueError("Position hors archive")
        self.position = position
        return position

    def read(self, size=-1):
        with self.lock:
            if size < 0:
                size = self.size - self.position
            size = min(size, self.size - self.position)
            if size == 0:
                return b""
            if size > 8 * 1024 * 1024:
                raise IOError("Lecture non bornée de l'archive refusée")
            start, end = self.position, self.position + size
            if start >= self._tail_offset:
                data = self._tail[start - self._tail_offset:end - self._tail_offset]
            else:
                data = self._request(f"bytes={start}-{end - 1}")
            self.position = end
            return data


def list_archive(url, cache_dir):
    remote = HTTPRangeFile(url, cache_dir)
    with zipfile.ZipFile(remote) as archive:
        entries = [{"filename": entry.filename, "bytes": entry.file_size,
                    "compressed_bytes": entry.compress_size, "compression": entry.compress_type,
                    "offset": entry.header_offset, "crc": entry.CRC}
                   for entry in archive.infolist()]
    return remote, entries


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--cache", default="cache/native-provider-validation/ranges")
    args = parser.parse_args()
    remote, entries = list_archive(args.url, args.cache)
    out = Path(args.cache).parent / (hashlib.sha256(args.url.encode()).hexdigest()[:16] + "-index.json")
    out.write_text(json.dumps({"url": args.url, "size": remote.size, "etag": remote.etag,
                               "last_modified": remote.last_modified, "entries": entries,
                               "http_records": remote.records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"index": str(out), "size": remote.size, "http_bytes": remote.requested_bytes,
                      "entries": len(entries), "sample": entries[:8]}, ensure_ascii=False))
