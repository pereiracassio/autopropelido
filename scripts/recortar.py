"""Deixa em vias.json e lugares.json só o que está dentro do município de Jacareí (o limite vem do OpenStreetMap)."""
import json, os, sys, time, urllib.request, urllib.parse

URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
Q = '[out:json][timeout:120];relation["boundary"="administrative"]["name"="Jacareí"]["admin_level"="8"];out geom;'


def baixar_limite():
    for tent in range(8):
        url = URLS[tent % len(URLS)]
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": Q}).encode(),
                                         headers={"User-Agent": "autopropelido-dados (github.com/pereiracassio/autopropelido)"})
            d = json.loads(urllib.request.urlopen(req, timeout=150).read())
            rels = d.get("elements", [])
            if not rels:
                raise RuntimeError("limite não encontrado")
            ways = []
            for m in rels[0]["members"]:
                if m["type"] == "way" and m.get("role", "outer") in ("outer", "") and m.get("geometry"):
                    ways.append([[p["lat"], p["lon"]] for p in m["geometry"]])
            print("limite: %d trechos" % len(ways), flush=True)
            return ways
        except Exception as ex:
            print("tentativa", tent, url, ex, flush=True)
            time.sleep(5)
    sys.exit("não consegui baixar o limite")


def segmentos(ways):
    segs = []
    for w in ways:
        for a, b in zip(w, w[1:]):
            segs.append((a[0], a[1], b[0], b[1]))
    return segs


def dentro(segs, lat, lon):
    # par ou ímpar: raio para o leste, conta quantos lados do limite cruza
    c = False
    for la1, lo1, la2, lo2 in segs:
        if (la1 > lat) != (la2 > lat):
            x = lo1 + (lat - la1) / (la2 - la1) * (lo2 - lo1)
            if x > lon:
                c = not c
    return c


if os.path.exists("limite.json"):
    ways = json.load(open("limite.json", encoding="utf-8"))
else:
    ways = baixar_limite()
    json.dump(ways, open("limite.json", "w", encoding="utf-8"), separators=(",", ":"))
segs = segmentos(ways)
lats = [s[0] for s in segs] + [s[2] for s in segs]
lons = [s[1] for s in segs] + [s[3] for s in segs]
S, N, W, E = min(lats), max(lats), min(lons), max(lons)
print("caixa do limite", S, N, W, E)


def ponto_dentro(lat, lon):
    return S <= lat <= N and W <= lon <= E and dentro(segs, lat, lon)


if os.path.exists("vias.json"):
    vias = json.load(open("vias.json", encoding="utf-8"))
    # a via fica se algum ponto dela está dentro do município (assim as que cruzam a divisa continuam inteiras)
    keep = [v for v in vias if any(ponto_dentro(p[0], p[1]) for p in v["g"][:: max(1, len(v["g"]) // 6)] + [v["g"][-1]])]
    print("vias: %d -> %d" % (len(vias), len(keep)))
    json.dump(keep, open("vias.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

if os.path.exists("lugares.json"):
    lug = json.load(open("lugares.json", encoding="utf-8"))
    keep = [l for l in lug if ponto_dentro(l[1], l[2])]
    print("lugares: %d -> %d" % (len(lug), len(keep)))
    json.dump(keep, open("lugares.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
