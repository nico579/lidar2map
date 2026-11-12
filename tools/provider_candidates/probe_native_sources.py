"""Recherches bornées et traçables des sources natives (hors catalogue actif)."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

CACHE = Path(__file__).resolve().parents[2] / "cache/native-provider-validation/http"


def fetch(url, limit=2_000_000, method="GET"):
    key = hashlib.sha256((method + " " + url + " " + str(limit)).encode()).hexdigest()[:20]
    CACHE.mkdir(parents=True, exist_ok=True)
    info_path = CACHE / (key + ".json")
    body_path = CACHE / (key + ".body")
    if info_path.exists() and body_path.exists():
        cached = json.loads(info_path.read_text(encoding="utf-8"))
        if "error" not in cached:
            return cached, body_path.read_bytes()
    info = {"url": url, "method": method, "date_utc": datetime.now(timezone.utc).isoformat()}
    body = b""
    try:
        with urlopen(Request(url, headers={"User-Agent": "lidar2map-native-validation/1.0"}, method=method), timeout=20) as response:
            info.update(status=response.status, final_url=response.url,
                        headers={k: v for k, v in response.headers.items() if k.lower() != "set-cookie"})
            body = response.read(limit + 1) if method != "HEAD" else b""
            info["truncated"] = len(body) > limit
            body = body[:limit]
            info.update(bytes_read=len(body), sha256=hashlib.sha256(body).hexdigest())
    except Exception as exc:
        info["error"] = str(exc)
    body_path.write_bytes(body)
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info, body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--head", action="store_true")
    parser.add_argument("--limit", type=int, default=2_000_000)
    args = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for info, body in pool.map(lambda url: fetch(url, limit=args.limit, method="HEAD" if args.head else "GET"), args.urls):
            print(json.dumps(info, ensure_ascii=False))
            content = body.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(content)
                print(json.dumps(parsed, ensure_ascii=False)[:18000])
            except ValueError:
                links = [link for link in re.findall(r'(?:href|src)=[\"\']([^\"\']+)', content)
                         if not any(word in link for word in ("favicon", ".png", ".svg", "javascript:", "#", "components/"))]
                print(json.dumps(links, ensure_ascii=False))


if __name__ == "__main__":
    main()
