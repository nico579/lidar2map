# Sondage Estonie : scripts/formulaires de la page p614 + plugin otsing.
import ssl, urllib.request, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0"}

def get(url, timeout=30, max_bytes=3_000_000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.headers.get("Content-Type", "?"), r.read(max_bytes)
    except Exception as e:
        return None, type(e).__name__ + ": " + str(e)[:120], b""

BASE = "https://geoportaal.maaamet.ee"
st, ct, data = get(BASE + "/est/ruumiandmed/korgusandmed/laadi-korgusandmed-alla-p614.html")
html = data.decode("utf-8", "replace")
print(f"[{st}] page p614 len={len(html)}")

for m in sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', html))):
    print("  script src:", m[:150])
for m in re.findall(r"<form[^>]*>", html):
    print("  form:", m[:220])
for m in re.findall(r'<iframe[^>]*src="([^"]+)"', html):
    print("  iframe:", m[:180])
# divs marqués pour le plugin
for m in re.findall(r'<[a-z]+[^>]*(?:id|class)="[^"]*otsing[^"]*"[^>]*>', html)[:8]:
    print("  otsing el:", m[:250])
# XHR/fetch dans le JS inline
for m in sorted(set(re.findall(r'(?:fetch|ajax|XMLHttpRequest|\.get|\.post)\(["\']([^"\']+)', html)))[:15]:
    print("  xhr:", m[:160])
