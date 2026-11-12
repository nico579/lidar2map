"""Inspection ponctuelle des configurations publiées par les portails officiels."""
from probe_native_sources import fetch

url = "https://zbgis.skgeodesy.sk/mapka/7104.d91c5f6dc5f62120.js"
body = fetch(url)[1].decode("utf-8")
for key in ('GPServer', '/export', 'ExportDMR', 'recaptcha', 'apiUrl', 'submitJob', 'serviceUrl', 'product/version'):
    pos = body.find(key)
    print(key, body[max(0, pos - 200):pos + 2300] if pos >= 0 else "ABSENT")
url = "https://geoportail.wallonie.be/catalogue/a004e570-99d6-4fe5-b83d-49b774409278.html"
body = fetch(url)[1].decode("utf-8")
for key in ("personnalis", "extraction", "form-download", "GEOTIFF_3812_PROV_BRABANT", "getfile"):
    pos = body.find(key)
    print(key, body[max(0, pos - 300):pos + 1700] if pos >= 0 else "ABSENT")
