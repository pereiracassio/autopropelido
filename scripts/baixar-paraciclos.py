"""Baixa do OpenStreetMap os paraciclos (lugares para prender bicicleta) de Jacareí e São José (paraciclos.json)."""
import json, os, subprocess, sys, time, urllib.request, urllib.parse

S, W, N, E = -23.45, -46.12, -23.00, -45.65
NL, NC = int(os.environ.get('GRADE', '4')), int(os.environ.get('GRADE', '4'))
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
pontos, vistos, falhas = [], set(), 0
chaves = set()
if os.environ.get('SOMAR') and os.path.exists('paraciclos.json'):
    pontos = json.load(open('paraciclos.json', encoding='utf-8'))
    chaves = set((x[0], x[1]) for x in pontos)


def salvar():
    with open("paraciclos.json", "w", encoding="utf-8") as f:
        json.dump(pontos, f, ensure_ascii=False, separators=(",", ":"))
    if os.environ.get("CI"):
        subprocess.run("git add paraciclos.json && git commit -q -m 'paraciclos: %d' && (git push -q || (git pull -q --rebase -X theirs && git push -q))" % len(pontos), shell=True)


for a in range(NL):
    for b in range(NC):
        s = S + (N - S) * a / NL
        n = S + (N - S) * (a + 1) / NL
        w = W + (E - W) * b / NC
        e = W + (E - W) * (b + 1) / NC
        bbox = "%.4f,%.4f,%.4f,%.4f" % (s, w, n, e)
        q = '[out:json][timeout:90];nwr["amenity"="bicycle_parking"](%s);out center tags;' % bbox
        ok = False
        for tent in range(4):
            url = URLS[tent % len(URLS)]
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(),
                                             headers={"User-Agent": "autopropelido-dados (github.com/pereiracassio/autopropelido)"})
                d = json.loads(urllib.request.urlopen(req, timeout=70).read())
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
                    if (round(lat, 5), round(lon, 5)) in chaves:
                        continue
                    chaves.add((round(lat, 5), round(lon, 5)))
                    pontos.append([round(lat, 5), round(lon, 5), t.get("name", ""), 1 if t.get("covered") == "yes" else 0, t.get("capacity", "")])
                print("ok", bbox, len(d["elements"]), flush=True)
                ok = True
                break
            except Exception as ex:
                print("tentativa", tent, url, bbox, ex, flush=True)
                time.sleep(5)
        if not ok:
            falhas += 1
        salvar()
        time.sleep(2)

print("paraciclos", len(pontos), "falhas", falhas)
if falhas:
    sys.exit(1)
