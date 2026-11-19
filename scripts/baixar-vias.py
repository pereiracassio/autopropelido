"""Baixa do OpenStreetMap as ruas e ciclovias de Jacareí e guarda em vias.json."""
import json, os, subprocess, sys, time, urllib.request, urllib.parse

S, W, N, E = -23.45, -46.12, -23.15, -45.80
NL, NC = 4, 4
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def consulta(bbox):
    return ('[out:json][timeout:120];('
            'way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"](%s);'
            'way["highway"="cycleway"](%s);'
            'way["highway"~"^(path|footway|pedestrian|track)$"]["bicycle"="designated"](%s);'
            ');out geom tags qt;') % (bbox, bbox, bbox)


vistos, vias, falhas = set(), [], 0


def salvar():
    with open("vias.json", "w", encoding="utf-8") as f:
        json.dump(vias, f, ensure_ascii=False, separators=(",", ":"))
    if os.environ.get("CI"):
        subprocess.run("git add vias.json && git commit -q -m 'vias: %d' && git push -q" % len(vias), shell=True)


for a in range(NL):
    for b in range(NC):
        s = S + (N - S) * a / NL
        n = S + (N - S) * (a + 1) / NL
        w = W + (E - W) * b / NC
        e = W + (E - W) * (b + 1) / NC
        bbox = "%.4f,%.4f,%.4f,%.4f" % (s, w, n, e)
        ok = False
        for tent in range(4):
            url = URLS[tent % len(URLS)]
            try:
                req = urllib.request.Request(
                    url,
                    data=urllib.parse.urlencode({"data": consulta(bbox)}).encode(),
                    headers={"User-Agent": "autopropelido-dados (github.com/pereiracassio/autopropelido)"})
                d = json.loads(urllib.request.urlopen(req, timeout=90).read())
                for el in d["elements"]:
                    if "geometry" not in el or el["id"] in vistos:
                        continue
                    vistos.add(el["id"])
                    vias.append({"i": el["id"], "t": el.get("tags", {}),
                                 "g": [[round(p["lat"], 5), round(p["lon"], 5)] for p in el["geometry"]]})
                print("ok", a, b, len(d["elements"]), flush=True)
                ok = True
                break
            except Exception as ex:
                print("tentativa", tent, url, a, b, ex, flush=True)
                time.sleep(5)
        if not ok:
            falhas += 1
        salvar()
        time.sleep(2)

print("vias", len(vias), "falhas", falhas)
if falhas:
    sys.exit(1)
