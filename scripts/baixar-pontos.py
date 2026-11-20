"""Baixa do OpenStreetMap lombadas, semáforos, pontos de recarga e lugares de conserto (pontos.json)."""
import json, os, subprocess, sys, time, urllib.request, urllib.parse

S, W, N, E = -23.45, -46.12, -23.00, -45.65
NL, NC = 4, 4
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
GUARDAR = ["name", "brand", "operator", "shop", "amenity", "craft", "highway", "traffic_calming", "opening_hours",
           "phone", "contact:phone", "website", "contact:website", "addr:street", "addr:housenumber", "capacity",
           "bicycle", "description"]


def consulta(bbox):
    return ('[out:json][timeout:120];('
            'node["traffic_calming"](%s);'
            'node["highway"="traffic_signals"](%s);'
            'nwr["amenity"~"^(charging_station|bicycle_repair_station)$"](%s);'
            'nwr["shop"~"^(bicycle|motorcycle|motorcycle_repair|scooter|e-bike|electronics_repair)$"](%s);'
            'nwr["craft"="electronics_repair"](%s);'
            ');out center tags;') % ((bbox,) * 5)


def tipo_de(t):
    if "traffic_calming" in t:
        return "lombada"
    if t.get("highway") == "traffic_signals":
        return "semaforo"
    if t.get("amenity") == "charging_station":
        return "recarga"
    if t.get("amenity") == "bicycle_repair_station":
        return "reparo"
    sh = t.get("shop")
    if sh == "bicycle":
        return "bicicletaria"
    if sh in ("motorcycle", "motorcycle_repair"):
        return "moto"
    if sh in ("scooter", "e-bike"):
        return "scooter"
    if sh == "electronics_repair" or t.get("craft") == "electronics_repair":
        return "eletronico"
    return None


pontos, vistos, falhas = [], set(), 0


def salvar():
    with open("pontos.json", "w", encoding="utf-8") as f:
        json.dump(pontos, f, ensure_ascii=False, separators=(",", ":"))
    if os.environ.get("CI"):
        subprocess.run("git add pontos.json && git commit -q -m 'pontos: %d' && (git push -q || (git pull -q --rebase -X theirs && git push -q))" % len(pontos), shell=True)


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
                    url, data=urllib.parse.urlencode({"data": consulta(bbox)}).encode(),
                    headers={"User-Agent": "autopropelido-dados (github.com/pereiracassio/autopropelido)"})
                d = json.loads(urllib.request.urlopen(req, timeout=100).read())
                for el in d["elements"]:
                    t = el.get("tags", {})
                    if el["type"] == "node":
                        lat, lon = el.get("lat"), el.get("lon")
                    else:
                        c = el.get("center") or {}
                        lat, lon = c.get("lat"), c.get("lon")
                    chave = (el["type"], el["id"])
                    tp = tipo_de(t)
                    if lat is None or tp is None or chave in vistos:
                        continue
                    vistos.add(chave)
                    pontos.append({"t": tp, "n": t.get("name", ""), "la": round(lat, 5), "lo": round(lon, 5),
                                   "g": {k: t[k] for k in GUARDAR if k in t or False} | {k: v for k, v in t.items() if k.startswith("service:")}})
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

print("pontos", len(pontos), "falhas", falhas)
if falhas:
    sys.exit(1)
