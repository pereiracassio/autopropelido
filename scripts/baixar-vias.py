"""Baixa do OpenStreetMap as ruas e ciclovias de Jacareí e guarda em vias.json."""
import json, os, subprocess, sys, time, urllib.request, urllib.parse

S, W, N, E = -23.45, -46.12, -23.15, -45.80
NL, NC = int(os.environ.get('GRADE_L', '4')), int(os.environ.get('GRADE_C', '4'))
REGIAO = os.environ.get('REGIAO')
if REGIAO:
    S, W, N, E = [float(x) for x in REGIAO.split(',')]
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
# SO="1,1;1,2" refaz só esses pedaços (grade 4x4), cada um dividido em SUB x SUB, e soma ao vias.json que já existe
SO = [tuple(map(int, t.split(","))) for t in os.environ.get("SO", "").split(";") if t]
SUB = int(os.environ.get("SUB", "1"))
if (SO or REGIAO) and os.path.exists("vias.json"):
    vias = json.load(open("vias.json", encoding="utf-8"))
    vistos = set(v["i"] for v in vias)


def salvar():
    with open("vias.json", "w", encoding="utf-8") as f:
        json.dump(vias, f, ensure_ascii=False, separators=(",", ":"))
    if os.environ.get("CI"):
        subprocess.run("git add vias.json && git commit -q -m 'vias: %d' && (git push -q || (git pull -q --rebase -X theirs && git push -q))" % len(vias), shell=True)


caixas = []
for a in range(NL):
    for b in range(NC):
        if SO and (a, b) not in SO:
            continue
        for c in range(SUB):
            for d in range(SUB):
                s0 = S + (N - S) * (a + c / SUB) / NL
                n0 = S + (N - S) * (a + (c + 1) / SUB) / NL
                w0 = W + (E - W) * (b + d / SUB) / NC
                e0 = W + (E - W) * (b + (d + 1) / SUB) / NC
                caixas.append((a, b, "%.4f,%.4f,%.4f,%.4f" % (s0, w0, n0, e0)))

for a, b, bbox in caixas:
    ok = False
    for tent in range(4):
        url = URLS[tent % len(URLS)]
        try:
            req = urllib.request.Request(
                url,
                data=urllib.parse.urlencode({"data": consulta(bbox)}).encode(),
                headers={"User-Agent": "autopropelido-dados (github.com/pereiracassio/autopropelido)"})
            d = json.loads(urllib.request.urlopen(req, timeout=150).read())
            for el in d["elements"]:
                if "geometry" not in el or el["id"] in vistos:
                    continue
                vistos.add(el["id"])
                vias.append({"i": el["id"], "t": el.get("tags", {}),
                             "g": [[round(p["lat"], 5), round(p["lon"], 5)] for p in el["geometry"]]})
            print("ok", a, b, bbox, len(d["elements"]), flush=True)
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
