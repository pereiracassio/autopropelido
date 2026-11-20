"""Olha o que o OpenStreetMap tem de caminhos e ciclovias perto da Avenida Davi Monteiro Lino."""
import json, time, urllib.request, urllib.parse
BBOX = "-23.300,-45.985,-23.270,-45.950"
Q = ('[out:json][timeout:90];('
     'way["highway"~"^(cycleway|footway|path|pedestrian|track|service|steps)$"](%s);'
     'way["bicycle"](%s);way["cycleway"](%s);way["cycleway:left"](%s);way["cycleway:right"](%s);way["cycleway:both"](%s);'
     'relation["route"="bicycle"](%s);'
     ');out tags center;') % ((BBOX,) * 7)
URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"]
for t in range(9):
    try:
        req = urllib.request.Request(URLS[t % 3], data=urllib.parse.urlencode({"data": Q}).encode(), headers={"User-Agent": "autopropelido-dados"})
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
        out = [{"tipo": e["type"], "id": e["id"], "centro": e.get("center"), "tags": e.get("tags", {})} for e in d["elements"]]
        json.dump(out, open("diagnostico.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print("ok", len(out)); break
    except Exception as ex:
        print("tentativa", t, ex, flush=True); time.sleep(5)
