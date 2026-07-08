#!/usr/bin/env python3
"""Build a self-contained HTML flow map: artifact origins -> (documented dealer/museum hub) -> British Museum.
Reads out/FINAL_bm_africa_provenance_master.csv, writes out/artifact_flows_map.html.
Marker size = record count; colour = share of Haiku 'unfair' verdicts; arcs routed via a hub
when the record's matched chain includes a documented hub entity (Umlauff->Hamburg, Ratton->Paris, ...).
"""
import csv, json, re, math
from collections import defaultdict

csv.field_size_limit(10_000_000)

GAZ = {  # place -> (lat, lon, pretty)
 "ghana": (7.95, -1.03, "Ghana"), "kumase": (6.69, -1.62, "Kumasi"), "kumasi": (6.69, -1.62, "Kumasi"),
 "manhyia palace": (6.70, -1.62, "Manhyia Palace, Kumasi"), "asante region": (6.75, -1.5, "Asante Region"),
 "democratic republic of congo": (-2.9, 23.6, "DR Congo"), "kasai": (-5.0, 22.4, "Kasai (DRC)"),
 "nigeria": (9.1, 8.7, "Nigeria"), "benin city": (6.34, 5.63, "Benin City"), "kano": (12.0, 8.52, "Kano"),
 "edo": (6.34, 5.63, "Edo (Benin City)"), "arochukwu": (5.39, 7.91, "Arochukwu"), "warri": (5.52, 5.75, "Warri"),
 "kano state": (12.0, 8.52, "Kano"), "tiya": (8.43, 38.61, "Tiya (Ethiopia)"), "bonwire": (6.8, -1.45, "Bonwire (Ghana)"),
 "lower congo": (-5.5, 14.5, "Lower Congo"),
 "royal palace": (6.70, -1.62, "Royal Palace, Kumasi"), "maqdala": (11.42, 39.31, "Maqdala"),
 "mushenge": (-4.63, 21.33, "Mushenge/Nsheng (Kuba capital)"), "lusambo": (-4.97, 23.44, "Lusambo (Sankuru, DRC)"),
 "ngomeni": (-28.7, 30.45, "Ngomeni (Msinga, KwaZulu-Natal)"), "durban": (-29.86, 31.02, "Durban"),
 "simien mountains": (13.25, 38.4, "Simien Mountains (Ethiopia)"), "cotonou": (6.36, 2.42, "Cotonou"),
 "mostagedda": (27.0, 31.3, "Mostagedda (Egypt)"), "abomey": (7.18, 1.99, "Abomey (Dahomey)"),
 "obuasi": (6.20, -1.66, "Obuasi (Ghana)"), "tugela ferry": (-28.74, 30.45, "Tugela Ferry (KZN)"),
 "rabuoi kano": (12.0, 8.52, "Kano"), "sokoto": (13.06, 5.24, "Sokoto"), "ife": (7.48, 4.56, "Ife"),
 "owo": (7.19, 5.59, "Owo"), "bida": (9.08, 6.01, "Bida"), "calabar": (4.96, 8.33, "Calabar"),
 "cross river state": (5.9, 8.6, "Cross River"), "ethiopia": (9.0, 39.5, "Ethiopia"),
 "addis ababa": (9.03, 38.74, "Addis Ababa"), "south africa": (-29.0, 25.0, "South Africa"),
 "kwazulu-natal": (-28.5, 31.0, "KwaZulu-Natal"), "natal": (-28.5, 31.0, "KwaZulu-Natal"),
 "bomvini": (-28.7, 31.4, "Bomvini (KZN)"), "nkandla forest": (-28.7, 31.1, "Nkandla (KZN)"),
 "japan": (36.0, 138.0, "Japan"), "republic of benin": (9.3, 2.3, "Republic of Benin"),
 "mutare": (-18.97, 32.65, "Mutare (Zimbabwe)"), "sudan": (15.5, 32.5, "Sudan"),
 "omdurman": (15.65, 32.48, "Omdurman"), "kenya": (0.5, 37.5, "Kenya"),
 "zimbabwe": (-19.0, 29.8, "Zimbabwe"), "great zimbabwe": (-20.27, 30.93, "Great Zimbabwe"),
 "uganda": (1.4, 32.3, "Uganda"), "cameroon": (5.7, 12.4, "Cameroon"), "somalia": (5.15, 46.2, "Somalia"),
 "djibouti": (11.6, 43.1, "Djibouti"), "madagascar": (-19.0, 46.7, "Madagascar"),
 "namibia": (-22.0, 17.0, "Namibia"), "gaborone": (-24.65, 25.91, "Gaborone"),
 "zambia": (-13.5, 28.0, "Zambia"), "chad": (13.5, 18.7, "Chad"), "malawi": (-13.5, 34.0, "Malawi"),
 "angola": (-12.3, 17.3, "Angola"), "china": (35.0, 105.0, "China"), "italy": (42.8, 12.8, "Italy"),
 "mali": (17.0, -4.0, "Mali"), "senegal": (14.5, -14.4, "Senegal"), "sierra leone": (8.5, -11.8, "Sierra Leone"),
 "liberia": (6.4, -9.4, "Liberia"), "tanzania": (-6.3, 34.8, "Tanzania"), "egypt": (26.8, 30.8, "Egypt"),
 "morocco": (31.8, -7.1, "Morocco"), "algeria": (28.0, 3.0, "Algeria"), "tunisia": (34.0, 9.0, "Tunisia"),
 "libya": (27.0, 17.0, "Libya"), "mozambique": (-18.6, 35.5, "Mozambique"), "botswana": (-22.3, 24.7, "Botswana"),
 "lesotho": (-29.6, 28.2, "Lesotho"), "swaziland": (-26.5, 31.5, "Eswatini"), "eswatini": (-26.5, 31.5, "Eswatini"),
 "rwanda": (-1.9, 29.9, "Rwanda"), "burundi": (-3.4, 29.9, "Burundi"), "gabon": (-0.8, 11.6, "Gabon"),
 "togo": (8.6, 1.0, "Togo"), "burkina faso": (12.3, -1.5, "Burkina Faso"), "niger": (17.6, 8.0, "Niger"),
 "gambia": (13.45, -15.3, "The Gambia"), "guinea": (10.4, -11.0, "Guinea"), "eritrea": (15.2, 39.0, "Eritrea"),
 "ivory coast": (7.5, -5.5, "Côte d'Ivoire"), "cote d'ivoire": (7.5, -5.5, "Côte d'Ivoire"),
 "sri lanka": (7.8, 80.7, "Sri Lanka"), "india": (21.0, 78.0, "India"), "africa": (2.0, 17.0, "Africa (unspecified)"),
 # rock-art photo sites (approximate, country-level clusters)
 "namoratung'a": (2.0, 36.05, "Namoratung'a (Kenya, approx.)"), "marsabit county": (2.33, 37.99, "Marsabit (Kenya)"),
 "turkana county": (3.1, 35.6, "Turkana (Kenya)"), "laga oda": (9.3, 41.6, "Laga Oda (Ethiopia, approx.)"),
 "por epic": (9.55, 41.87, "Porc-Épic (Ethiopia)"), "moite": (3.6, 36.6, "Moite (Kenya, approx.)"),
 "goda ajewa": (9.3, 41.5, "Goda Ajewa (Ethiopia, approx.)"), "saka sharifa": (9.3, 41.5, "Saka Sharifa (Ethiopia, approx.)"),
 "oromitire": (9.3, 41.5, "Oromitire (Ethiopia, approx.)"), "afgaba": (9.3, 41.5, "Afgaba (Ethiopia, approx.)"),
 "surima": (2.5, 36.5, "Surima (Kenya, approx.)"), "anye-nangiliko": (2.5, 36.5, "Anye-Nangiliko (Kenya, approx.)"),
 "kang'itit": (2.5, 36.5, "Kang'itit (Kenya, approx.)"), "marti": (1.7, 37.0, "Marti (Kenya, approx.)"),
}
COUNTRY_FALLBACK = ["nigeria", "ghana", "ethiopia", "sudan", "kenya", "uganda", "tanzania", "cameroon",
 "zimbabwe", "zambia", "malawi", "angola", "namibia", "botswana", "lesotho", "madagascar", "somalia",
 "mozambique", "senegal", "mali", "togo", "gabon", "rwanda", "burundi", "eritrea", "egypt", "morocco",
 "algeria", "tunisia", "libya", "guinea", "gambia", "liberia", "sierra leone", "chad", "niger",
 "south africa", "democratic republic of congo", "republic of benin", "japan", "china", "india", "italy"]

HUBS = {  # hub id -> (lat, lon, label, entity keywords)
 "hamburg": (53.55, 10.0, "Hamburg", ["umlauff", "konietzko", "hagenbeck", "o'swald", "woermann", "gaiser", "hansing", "godeffroy", "völkerkunde hamburg", "markk"]),
 "berlin": (52.52, 13.4, "Berlin", ["speyer", "luschan", "ethnological museum of berlin", "bastian", "charité", "s-sammlung", "prussian cultural heritage"]),
 "paris": (48.86, 2.35, "Paris", ["ratton", "guillaume", "ascher", "trocadéro", "musée de l'homme", "quai branly", "verreaux"]),
 "brussels": (50.85, 4.35, "Brussels/Antwerp", ["pareyn", "walschot", "tervuren", "africamuseum"]),
 "liverpool": (53.41, -2.99, "Liverpool", ["ridyard", "elder dempster"]),
 "new_york": (40.71, -74.0, "New York", ["simpson, merton", "merton daniel simpson", "klejman", "komor", "kamer", "american museum of natural history"]),
}
BM = (51.519, -0.127)
PLACE_PREFIX = re.compile(r'^[A-Za-z/\' ]{2,30}:\s*')

def norm_place(v):
    v = (v or '').strip()
    if not v: return None
    v = v.split(';')[0]
    v = PLACE_PREFIX.sub('', v).strip()
    v = v.split('(')[0].strip().rstrip('.')
    return v or None

def locate(v):
    if not v: return None
    k = v.lower()
    if k in GAZ: return GAZ[k]
    for c in COUNTRY_FALLBACK:
        if c in k: return GAZ[c]
    return None

def pick_hub(entities):
    e = (entities or '').lower()
    for hid, (_la, _lo, _lab, kws) in HUBS.items():
        if any(kw in e for kw in kws): return hid
    return None

CATS = ["unfair", "transactional", "insufficient_evidence", "fair", "not_shortlisted"]
origins = defaultdict(lambda: {"n": 0, "cats": dict.fromkeys(CATS, 0), "ents": defaultdict(int), "regs": []})
flows = defaultdict(lambda: dict.fromkeys(CATS, 0))
unmapped = defaultdict(int)
skipped_local = 0

rows = list(csv.DictReader(open('out/FINAL_bm_africa_provenance_master.csv', encoding='utf-8')))
skipped_asia = 0
skipped_nonafrica = 0
for r in rows:
    if r.get('dept') == 'Asia':  # 'Edo' keyword-slice homonym pulled in Japanese Edo-period material
        skipped_asia += 1
        continue
    # find spot first (where the object's journey to the BM began), production place as fallback
    raw = norm_place(r['find_spot']) or norm_place(r['production_place'])
    if raw and raw.lower() in ("british museum", "london", "llantrisant", "united kingdom", "england", "british isles"):
        skipped_local += 1
        continue
    loc = locate(raw)
    if not loc:
        unmapped[raw or "(no place recorded)"] += 1
        continue
    if not (-36.0 <= loc[0] <= 38.0 and -18.5 <= loc[1] <= 52.0):  # Africa bounding box
        skipped_nonafrica += 1  # e.g. Japanese charm in the Money & Medals slice, 'claimed to be from Italy' rows
        continue
    key = (loc[0], loc[1], loc[2])
    o = origins[key]
    o["n"] += 1
    cat = r["haiku_verdict"] if r["haiku_verdict"] in CATS else "not_shortlisted"
    o["cats"][cat] += 1
    for e in (r["matched_entities"] or "").split(";"):
        e = e.strip()
        if e: o["ents"][e] += 1
    if len(o["regs"]) < 3 and cat == "unfair": o["regs"].append(r["reg_number"])
    hub = pick_hub(r["matched_entities"])
    flows[(key, hub)][cat] += 1

data = {
 "origins": [{"lat": k[0], "lon": k[1], "name": k[2], "n": v["n"], "cats": v["cats"],
              "ents": sorted(v["ents"].items(), key=lambda x: -x[1])[:5], "regs": v["regs"]}
             for k, v in origins.items()],
 "flows": [{"from": [k[0][0], k[0][1]], "hub": k[1], "cats": v} for k, v in flows.items()],
 "hubs": {hid: {"lat": h[0], "lon": h[1], "label": h[2]} for hid, h in HUBS.items()},
 "bm": BM, "cats": CATS,
 "meta": {"total": len(rows), "mapped": sum(o["n"] for o in origins.values()),
          "skipped_uk_origin": skipped_local, "skipped_asia_dept": skipped_asia,
          "skipped_nonafrica": skipped_nonafrica,
          "unmapped": sorted(unmapped.items(), key=lambda x: -x[1])[:15],
          "unmapped_total": sum(unmapped.values())},
}

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>BM Africa corpus — artifact origins and movement to the British Museum</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
 html,body{margin:0;height:100%;font-family:Georgia,serif}
 #map{height:100%}
 .panel{position:absolute;z-index:1000;background:rgba(255,255,255,.94);border-radius:8px;
        box-shadow:0 1px 8px rgba(0,0,0,.25);padding:10px 14px;font-size:13px;line-height:1.45}
 #title{top:12px;left:54px;max-width:520px}
 #title h1{margin:0 0 2px;font-size:17px} #title p{margin:2px 0;color:#444;font-size:12px}
 #controls{bottom:18px;left:12px}
 #legend{bottom:18px;right:12px;max-width:260px}
 .sw{display:inline-block;width:11px;height:11px;border-radius:6px;margin-right:5px;vertical-align:-1px}
 label{display:block;cursor:pointer}
 .grad{height:10px;width:180px;background:linear-gradient(to right,#9aa7b3,#e0b34c,#c62828);border-radius:5px}
 .hubicon{background:#274b8f;border:2px solid #fff;border-radius:2px}
 .bmicon{background:#111;border:2px solid #fff;border-radius:50%}
</style></head><body>
<div id="map"></div>
<div class="panel" id="title">
 <h1>African artifacts in the British Museum — origins and routes</h1>
 <p>__MAPPED__ of __TOTAL__ records mapped · circle size = number of objects · colour = share judged
 <b style="color:#c62828">unfair</b> by the Haiku adjudicator · arcs show movement to the BM, routed through a
 dealer/museum hub when the documented chain names one (Umlauff→Hamburg, Ratton→Paris, Pareyn→Brussels…).</p>
 <p style="color:#666">Verdicts are automated <i>review signals from documented provenance associations — not determinations</i>. __UNMAPPED__ records had unmappable place text; __SKIP__ UK-made records (e.g. BM photographs), __SKIPASIA__ Asia-department records (Japanese Edo-period material caught by the corpus's 'Edo' keyword slice), and __SKIPNONAF__ other non-African origins are omitted.</p>
</div>
<div class="panel" id="controls"><b>Show verdicts</b><div id="checks"></div></div>
<div class="panel" id="legend">
 <b>Legend</b><br>
 <div class="grad"></div>
 <div style="display:flex;justify-content:space-between;width:180px;font-size:11px"><span>0% unfair</span><span>100%</span></div>
 <span class="sw" style="background:#111"></span>British Museum (destination)<br>
 <span class="sw" style="background:#274b8f;border-radius:2px"></span>documented market/museum hub<br>
 <span style="color:#888;font-size:12px">Arc width ∝ objects on that route</span>
</div>
<script>
const DATA = __DATA__;
const map = L.map('map',{worldCopyJump:true}).setView([14,10],3);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
 {attribution:'&copy; OpenStreetMap contributors &copy; CARTO', subdomains:'abcd', maxZoom:10}).addTo(map);

const active = new Set(DATA.cats);
const layer = L.layerGroup().addTo(map);

function colr(share){ // grey -> amber -> red
  const stops=[[154,167,179],[224,179,76],[198,40,40]];
  const t=Math.max(0,Math.min(1,share)), i=t<0.5?0:1, f=(t<0.5?t*2:(t-0.5)*2);
  const a=stops[i], b=stops[i+1];
  return `rgb(${Math.round(a[0]+(b[0]-a[0])*f)},${Math.round(a[1]+(b[1]-a[1])*f)},${Math.round(a[2]+(b[2]-a[2])*f)})`;
}
function arc(from,to,bend){
  const pts=[], n=24;
  const mx=(from[0]+to[0])/2, my=(from[1]+to[1])/2;
  const dx=to[0]-from[0], dy=to[1]-from[1], d=Math.sqrt(dx*dx+dy*dy)||1;
  const ox=-dy/d*bend, oy=dx/d*bend;
  const c=[mx+ox,my+oy];
  for(let i=0;i<=n;i++){const t=i/n;
    pts.push([(1-t)*(1-t)*from[0]+2*(1-t)*t*c[0]+t*t*to[0],
              (1-t)*(1-t)*from[1]+2*(1-t)*t*c[1]+t*t*to[1]]);}
  return pts;
}
function counts(cats){let n=0,u=0;for(const c of DATA.cats){if(active.has(c)){n+=cats[c]||0;if(c==='unfair')u+=cats[c]||0;}}return [n,u];}
function render(){
  layer.clearLayers();
  // flows: origin -> hub -> BM
  const hubTotals={};
  for(const f of DATA.flows){
    const [n,u]=counts(f.cats); if(!n) continue;
    const share=u/n, w=Math.max(0.6,Math.log2(n)*0.9), op=0.35+0.45*share;
    const col=colr(share);
    if(f.hub){
      const h=DATA.hubs[f.hub];
      L.polyline(arc(f.from,[h.lat,h.lon],4),{color:col,weight:w,opacity:op}).addTo(layer);
      hubTotals[f.hub]=(hubTotals[f.hub]||0)+n;
    } else {
      L.polyline(arc(f.from,DATA.bm,6),{color:col,weight:w,opacity:op}).addTo(layer);
    }
  }
  for(const hid in hubTotals){
    const h=DATA.hubs[hid];
    L.polyline(arc([h.lat,h.lon],DATA.bm,2),{color:'#274b8f',weight:Math.max(1,Math.log2(hubTotals[hid])),opacity:.7,dashArray:'4 3'}).addTo(layer);
    L.marker([h.lat,h.lon],{icon:L.divIcon({className:'hubicon',iconSize:[10,10]})}).addTo(layer)
     .bindPopup(`<b>${h.label}</b><br>documented hub in the chain of <b>${hubTotals[hid]}</b> shown objects`);
  }
  // origins
  for(const o of DATA.origins){
    const [n,u]=counts(o.cats); if(!n) continue;
    const share=u/n;
    const m=L.circleMarker([o.lat,o.lon],{radius:Math.max(3,Math.sqrt(n)*0.75),
      color:'#fff',weight:1,fillColor:colr(share),fillOpacity:.85}).addTo(layer);
    const ents=o.ents.map(e=>`${e[0]} (${e[1]})`).join('<br>');
    m.bindPopup(`<b>${o.name}</b> — ${n} object${n>1?'s':''}<br>`+
      `unfair: <b>${o.cats.unfair}</b> · transactional: ${o.cats.transactional} · `+
      `insufficient: ${o.cats.insufficient_evidence} · fair: ${o.cats.fair} · not shortlisted: ${o.cats.not_shortlisted}`+
      (ents?`<br><br><b>Top matched chain entities</b><br>${ents}`:'')+
      (o.regs.length?`<br><br>e.g. ${o.regs.join(', ')}`:''));
  }
  L.marker(DATA.bm,{icon:L.divIcon({className:'bmicon',iconSize:[14,14]})}).addTo(layer)
   .bindPopup('<b>British Museum, London</b><br>destination of all mapped flows');
}
const box=document.getElementById('checks');
const labels={unfair:'unfair',transactional:'transactional',insufficient_evidence:'insufficient evidence',fair:'fair',not_shortlisted:'not shortlisted (no KB match)'};
for(const c of DATA.cats){
  const l=document.createElement('label');
  l.innerHTML=`<input type="checkbox" checked data-c="${c}"> ${labels[c]}`;
  l.querySelector('input').onchange=e=>{e.target.checked?active.add(c):active.delete(c);render();};
  box.appendChild(l);
}
render();
</script></body></html>"""

html = (HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__TOTAL__", f"{data['meta']['total']:,}")
            .replace("__MAPPED__", f"{data['meta']['mapped']:,}")
            .replace("__UNMAPPED__", f"{data['meta']['unmapped_total']:,}")
            .replace("__SKIP__", f"{data['meta']['skipped_uk_origin']:,}")
            .replace("__SKIPASIA__", f"{data['meta']['skipped_asia_dept']:,}")
            .replace("__SKIPNONAF__", f"{data['meta']['skipped_nonafrica']:,}"))
open('out/artifact_flows_map.html', 'w', encoding='utf-8').write(html)
print(f"mapped {data['meta']['mapped']} / {data['meta']['total']}  (unmapped {data['meta']['unmapped_total']}, uk-origin skipped {data['meta']['skipped_uk_origin']})")
print("origins:", len(data['origins']), "| flows:", len(data['flows']))
print("top unmapped:", data['meta']['unmapped'][:8])
