"""Baixa do OpenStreetMap os lugares com nome de Jacareí (comércios, serviços, bairros) em lugares.json."""
import json, sys, time, urllib.request, urllib.parse

S, W, N, E = -23.45, -46.12, -23.15, -45.80
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
CHAVES = ["amenity", "shop", "leisure", "tourism", "office", "healthcare", "craft"]


def consulta(bbox):
    partes = "".join('nwr["name"]["%s"](%s);' % (c, bbox) for c in CHAVES)
    partes += 'nwr["name"]["place"~"^(suburb|neighbourhood|quarter|village|hamlet|town|city_block)$"](%s);' % bbox
    return '[out:json][timeout:120];(' + partes + ');out center tags;'


lugares, vistos, falhas = [], set(), 0
for a in range(2):
    for b in range(2):
        s = S + (N - S) * a / 2
        n = S + (N - S) * (a + 1) / 2
        w = W + (E - W) * b / 2
        e = W + (E - W) * (b + 1) / 2
        bbox = "%.4f,%.4f,%.4f,%.4f" % (s, w, n, e)
        ok = False
        for tent in range(6):
            url = URLS[tent % len(URLS)]
            try:
                req = urllib.request.Request(
                    url, data=urllib.parse.urlencode({"data": consulta(bbox)}).encode(),
                    headers={"User-Agent": "autopropelido-dados (github.com/pereiracassio/autopropelido)"})
                d = json.loads(urllib.request.urlopen(req, timeout=150).read())
                for el in d["elements"]:
                    t = el.get("tags", {})
                    if el["type"] == "node":
                        lat, lon = el.get("lat"), el.get("lon")
                    else:
                        c = el.get("center") or {}
                        lat, lon = c.get("lat"), c.get("lon")
                    chave = (el["type"], el["id"])
                    if lat is None or chave in vistos:
                        continue
                    vistos.add(chave)
                    tipo = next((t[c] for c in CHAVES + ["place"] if c in t), "")
                    lugares.append([t["name"], round(lat, 5), round(lon, 5), tipo])
                print("ok", bbox, len(d["elements"]), flush=True)
                ok = True
                break
            except Exception as ex:
                print("tentativa", tent, url, bbox, ex, flush=True)
                time.sleep(5)
        if not ok:
            falhas += 1

print("lugares", len(lugares), "falhas", falhas)
if falhas:
    sys.exit(1)
with open("lugares.json", "w", encoding="utf-8") as f:
    json.dump(lugares, f, ensure_ascii=False, separators=(",", ":"))
