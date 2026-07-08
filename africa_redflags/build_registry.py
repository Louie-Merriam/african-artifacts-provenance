#!/usr/bin/env python3
"""Build the pan-African red-flag registry from per-source files.

Inputs:  sources/*.json   (rich entries per mined source)
Outputs: africa_actors.json                  merged, deduplicated, sourced registry
         flat/<source>_actors.json           per-source flat alias lists (digitalbenin_actors.json format)
         flat/africa_all_actors.json         merged flat alias list
         patches/redflags_africa_patch.json  actors/channels entries in the KB schema
         patches/redflags_watchlist_v4_patch.json  named_actors additions for the rule scorer
         SOURCES.md                          every name -> documentary basis
         COVERAGE.md                         names per episode/region, exclusions, gaps
Conventions per handoff §3: both name orders as aliases, no bare common surnames,
why_flag = suspicion signal not proof. Entries may carry "matching":
  exclude_all      -> registry only (not KB patch, not flat)
  exclude_flat     -> KB patch yes, flat matching lists no (high-volume/generic)
  context_required -> flat yes, but only qualified alias forms (kept as authored)
"""
import json, os, re, unicodedata
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "sources")
os.makedirs(os.path.join(ROOT, "flat"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "patches"), exist_ok=True)

SOURCE_FILES = ["ora.json", "proveana_paese.json", "episodes_british.json",
                "episodes_german.json", "episodes_french_belgian.json", "market.json"]

# canonical-name merge map: variant (casefolded) -> canonical
MERGE = {
    "royal niger company (british episodes)": "royal niger company",
    "basler mission": "basel mission",
    "royal museum for central africa (tervuren)": "royal museum for central africa acquisitions 1897-1960 (tervuren)",
    "oskar marx (togo)": "ferdinand oskar marx",
    "georg zenker": "georg august zenker",
}

STOP_SINGLE = True  # drop 1-token aliases outright

def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def norm_key(name):
    n = fold(name).casefold().strip()
    n = re.sub(r"\s+", " ", n)
    return MERGE.get(n, MERGE.get(name.casefold(), n))

def is_person(entry):
    return "role" in entry  # actors have role, channels have type

def strip_paren(a):
    return re.sub(r"\s*\([^)]*\)", "", a).strip().strip(",").strip()

PARTICLES = {"von", "van", "de", "der", "du", "le", "la", "zu", "di", "da", "ter", "ten"}

def alias_variants(entry):
    """Enforce §3: both name orders, ASCII-folded forms, paren-stripped forms.
    context_required entries keep ONLY their authored qualified forms (no auto-generation
    that could re-create a bare common name)."""
    out = []
    seen = set()
    guarded = entry.get("matching") == "context_required"
    def add(a):
        a = re.sub(r"\s+", " ", a.strip())
        if not a: return
        k = a.casefold()
        if k in seen: return
        seen.add(k); out.append(a)
    def addf(a):
        add(a)
        f = fold(a)
        if f != a: add(f)
    for a in [entry["name"]] + entry.get("aliases", []):
        addf(a)
        if guarded:
            continue
        core = strip_paren(a)
        if core and core != a:
            addf(core)
        if is_person(entry) and core and not re.search(r"\d", core):
            if "," in core:
                parts = [p.strip() for p in core.split(",", 1)]
                if len(parts) == 2 and parts[0] and parts[1]:
                    addf(f"{parts[1]} {parts[0]}")
            else:
                toks = core.split()
                if len(toks) >= 2 and len(toks[-1]) > 2:
                    if len(toks) >= 3 and toks[-2].casefold() in PARTICLES:
                        addf(f"{toks[-2]} {toks[-1]}, {' '.join(toks[:-2])}")
                    else:
                        addf(f"{toks[-1]}, {' '.join(toks[:-1])}")
    return out

def flat_ok(alias):
    """Alias eligible for word-boundary matching lists: >=2 tokens, no bare parenthetical leftovers."""
    a = strip_paren(alias)
    toks = [t for t in re.split(r"[\s,]+", a) if t]
    if len(toks) < 2: return False
    if all(len(t) <= 2 for t in toks): return False
    return True

def slug(name):
    s = fold(name).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:48]

merged = {}          # key -> merged entry
order = []           # stable order of keys
for fn in SOURCE_FILES:
    path = os.path.join(SRC, fn)
    data = json.load(open(path, encoding="utf-8"))
    sid = data["source_id"]
    for kind in ("actors", "channels"):
        for e in data.get(kind, []):
            key = (kind, norm_key(e["name"]))
            if key not in merged:
                merged[key] = {
                    "kind": kind, "name": e["name"], "aliases": [], "episode_tags": [],
                    "region": e.get("region", ""), "why_flag": e["why_flag"],
                    "sources": [], "source_registries": [], "matching": e.get("matching", "include"),
                }
                merged[key]["role" if kind == "actors" else "type"] = e.get("role") or e.get("type", "")
                order.append(key)
            m = merged[key]
            # union aliases / tags / sources; prefer longest why_flag; strictest matching flag
            for a in [e["name"]] + e.get("aliases", []):
                if a.casefold() not in {x.casefold() for x in m["aliases"]}:
                    m["aliases"].append(a)
            for t in e.get("episode_tags", []):
                if t not in m["episode_tags"]: m["episode_tags"].append(t)
            if e.get("source") and e["source"] not in m["sources"]:
                m["sources"].append(e["source"])
            if sid not in m["source_registries"]: m["source_registries"].append(sid)
            if len(e.get("why_flag", "")) > len(m["why_flag"]): m["why_flag"] = e["why_flag"]
            sev = {"include": 0, "context_required": 1, "exclude_flat": 2, "exclude_all": 3}
            if sev[e.get("matching", "include")] > sev[m["matching"]]: m["matching"] = e.get("matching", "include")
            if e.get("region") and not m["region"]: m["region"] = e["region"]

# ---- expand aliases per conventions ----
for key in order:
    m = merged[key]
    m["aliases"] = alias_variants(m)

actors = [merged[k] for k in order if merged[k]["kind"] == "actors"]
channels = [merged[k] for k in order if merged[k]["kind"] == "channels"]

# ---- 1. merged rich registry ----
rich = {
    "description": "Pan-African red-flag registry of actors and channels documented as handling looted/coercively-acquired African cultural objects and human remains. Every entry is a suspicion signal for provenance review, NOT proof of wrongdoing; these actors also handled legitimately acquired material. Built from ORA, Proveana, PAESE, episode scholarship, and market research. See SOURCES.md and COVERAGE.md.",
    "conventions": "aliases include surname-first and forename-first plus ASCII-folded forms; matching field: include | context_required | exclude_flat (KB only, too generic/high-volume) | exclude_all (registry note only).",
    "actors": [{k: v for k, v in a.items() if k != "kind"} for a in actors],
    "channels": [{k: v for k, v in c.items() if k != "kind"} for c in channels],
}
json.dump(rich, open(os.path.join(ROOT, "africa_actors.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---- 2. per-source + merged flat lists ----
def flat_aliases(entries, registry=None):
    out, seen = [], set()
    for e in entries:
        if e["matching"] in ("exclude_flat", "exclude_all"): continue
        if registry and registry not in e["source_registries"]: continue
        for a in e["aliases"]:
            if not flat_ok(a): continue
            k = a.casefold()
            if k in seen: continue
            seen.add(k); out.append(a)
    return sorted(out, key=str.casefold)

flat_map = {"ora": "ora_actors.json", "proveana_paese": "proveana_paese_actors.json",
            "episodes_british": "episodes_british_actors.json", "episodes_german": "episodes_german_actors.json",
            "episodes_french_belgian": "episodes_french_belgian_actors.json", "market": "market_actors.json"}
all_entries = actors + channels
for sid, fn in flat_map.items():
    payload = {"source": sid, "named_actors": flat_aliases(all_entries, sid)}
    json.dump(payload, open(os.path.join(ROOT, "flat", fn), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump({"source": "africa_redflags_merged_v1", "named_actors": flat_aliases(all_entries)},
          open(os.path.join(ROOT, "flat", "africa_all_actors.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---- 3. KB patch (redflags_africa.json schema) ----
patch = {"_note": "Merge these into redflags_africa.json. actors: {id,name,aliases,role,why_flag}; channels: {id,name,aliases,type,why_flag}. Entries with matching=exclude_flat are included here for Haiku context but consider keeping them out of the shortlister's alias match if volume is a concern; exclude_all entries are omitted.",
         "actors": [], "channels": []}
for a in actors:
    if a["matching"] == "exclude_all": continue
    patch["actors"].append({"id": "axr_a_" + slug(a["name"]), "name": a["name"],
                            "aliases": [x for x in a["aliases"] if flat_ok(x)] or a["aliases"],
                            "role": a.get("role", ""),
                            "why_flag": a["why_flag"] + " [suspicion signal for review, not proof; source: " + "; ".join(a["sources"])[:400] + "]"})
for c in channels:
    if c["matching"] == "exclude_all": continue
    patch["channels"].append({"id": "axr_c_" + slug(c["name"]), "name": c["name"],
                              "aliases": [x for x in c["aliases"] if flat_ok(x)] or c["aliases"],
                              "type": c.get("type", ""),
                              "why_flag": c["why_flag"] + " [suspicion signal for review, not proof; source: " + "; ".join(c["sources"])[:400] + "]"})
json.dump(patch, open(os.path.join(ROOT, "patches", "redflags_africa_patch.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---- 4. watchlist v4 patch ----
json.dump({"_note": "Append these alias strings to named_actors in redflags_watchlist_v4.json (or drop this file beside digitalbenin_actors.json for auto-merge).",
           "source": "africa_redflags_merged_v1", "named_actors": flat_aliases(all_entries)},
          open(os.path.join(ROOT, "patches", "redflags_watchlist_v4_patch.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---- 5. SOURCES.md ----
lines = ["# SOURCES — documentary basis for every watchlist name\n",
         "Every entry below is a *documented provenance association*: a suspicion signal for review, not proof of wrongdoing.",
         "Registries: ora = Open Restitution Africa case studies; proveana_paese = Proveana (German Lost Art Foundation) + PAESE index entries (index-derived flags note the registry's occupation/context tags; Proveana person URLs follow the site's slug pattern, spot-verified); episodes_* = web-verified episode research; market = tribal-art market research.\n"]
for kind, items in (("Actors", actors), ("Channels", channels)):
    lines.append(f"\n## {kind}\n")
    for e in sorted(items, key=lambda x: fold(x["name"]).casefold()):
        flag = "" if e["matching"] == "include" else f"  **[{e['matching']}]**"
        lines.append(f"- **{e['name']}** ({', '.join(e['source_registries'])}){flag}")
        for s in e["sources"]:
            lines.append(f"  - {s}")
open(os.path.join(ROOT, "SOURCES.md"), "w", encoding="utf-8").write("\n".join(lines))

# ---- 6. COVERAGE.md ----
tagc, regc = Counter(), Counter()
for e in all_entries:
    for t in e["episode_tags"]: tagc[t] += 1
    r = (e.get("region") or "other").split("/")[0].strip()
    regc[r] += 1
excl_flat = [e["name"] for e in all_entries if e["matching"] == "exclude_flat"]
excl_all = [e["name"] for e in all_entries if e["matching"] == "exclude_all"]
ctx = [e["name"] for e in all_entries if e["matching"] == "context_required"]
flat_all = flat_aliases(all_entries)
cov = ["# COVERAGE REPORT — pan-African red-flag registry\n",
       f"Actors: **{len(actors)}**  ·  Channels: **{len(channels)}**  ·  Flat matchable aliases: **{len(flat_all)}**",
       f"Per-source: " + ", ".join(f"{sid}: {sum(1 for e in all_entries if sid in e['source_registries'])}" for sid in flat_map), "",
       "## Names per episode tag\n"]
for t, n in tagc.most_common():
    cov.append(f"- {t}: {n}")
cov.append("\n## Names per (primary) region\n")
for r, n in regc.most_common():
    cov.append(f"- {r}: {n}")
cov += ["\n## Deliberate exclusions from matching\n",
        f"- **Excluded from flat lists (KB-context only, too generic/high-volume):** {', '.join(excl_flat)}",
        f"- **Registry-note only (unverified lead, do not match):** {', '.join(excl_all)}",
        f"- **Context-required (qualified aliases only — common surnames):** {', '.join(ctx)}",
        "- **Dropped during curation:** Gene Hackman, Art Linson (ORA vigango donor line — ORA states acquisition circumstances unknown, no wrongdoing implied; weak signal, high-profile false-positive risk); A.F. Wallace, Henry Taylor (marginal custody links, common names); British Museum & Natural History Museum London as channels (self-referential in a BM-records pipeline); Everard im Thurn (no documented African material — seed removed); Fortnum & Mason (seed unverified — no source found); 'Christie's 1874 Asante sale' (unconfirmed; documented 1874 dispersals: Cape Coast prize auction, Garrard sale, Crown Agents); Glendining & Co, CMS sales, Hélène Leloup, Ralph Nash (see market source_note).",
        "\n## Known gaps / next passes\n",
        "- **BM corpus frequency analysis (handoff §7 step 1) still pending** — needs bm_africa_corpus.csv (folder not connected).",
        "- Sierra Leone 1898 hut-tax war: no named UK taker/holder verified; try West India Regiment provenance lines.",
        "- Aro expedition 1901-02: shrine destruction documented, no individual taker verified (Charles Partridge is the nearest sourced collector).",
        "- Sokoto 1903: no officer-level looter names verified beyond campaign command (Lugard); watch the Sokoto caliphate 'Red List' catalogue announced 2022.",
        "- Madagascar: only 3 names (Duchesne, Gallieni, G. Richard); French officer-level takers unresearched.",
        "- Zulu 1879: names from one regimental catalogue (Royal Welsh); other NMS 'Baggage and Belonging' regimental PDFs at files.nms.ac.uk remain unmined — each has object-level 'taken by' attributions across Maqdala/Asante/Zulu/Sudan/Niger campaigns.",
        "- ORA dataplatform (dataplatform.openrestitution.africa) is a client-rendered SPA — not mined; revisit with browser tooling.",
        "- A few PAESE recipient-museum channel entries were lost to extraction limits (full agent output preserved in session tool-results).",
        "- Bulk-extraction candidates: 'Atlas der Abwesenheit' (Savoy/Gouaffo 2023 — ~40,000 Cameroon objects across 45 German museums, with actor biographies; EN PDF at TU Berlin, data at DepositOnce); BM Collection Online biography term pages (enumerate objects per named colonial actor); AFROMET treasure database; SPK human-remains provenance volumes (East Africa 2023, West Africa 2026); Waterfield & King 'Provenance' (2006) for London dealers.",
        "\n## Validation shakeout (run once pipeline files are connected)\n",
        "Expect these laundered non-Benin cases to flag: Maqdala manuscript with Quaritch/Meux line; Namibian object with Luschan/Zürn/Charité line; BM Kuba material via Torday; Congo object with Pareyn→Wellcome line; Asante gold with Garrard 1874 or Crown Agents 1876/1900 line; Ethiopian item 'donated by the Secretary of State for India, 1868'; Cameroon Grassfields object with Conrau/Glauning/Strümpell line; Zimbabwe soapstone with Ancient Ruins Company line.",
        "\n## Structural pattern for the laundering rule\n",
        "[colonial extraction] → [soldier/missionary/shipping/exhibition conduit] → [specialist dealer: Webster/Oldman/Fenton/Umlauff/Speyer/Guillaume/Ratton] → [collector museum: Beasley/Hooper/Wellcome/Lever/Coray/Müller/Farnham] → [20th-c. dispersal: Stevens'/Hooper 1976/Wellcome rounds/Farnham sales or dealers Hewett/Ohly/Burney/Kamer/Klejman/Simpson/Komor] → [accession with 'clean' recent provenance]. Chains that START at a dispersal-stage name are truncated — the laundering-override rule should key on any actor/channel hit anywhere in the chain.",
        "\n## German structural rule\n",
        "1889 Bundesrat resolution (extended 1896): all items appropriated by German civil servants/military/state expeditions went to the Berlin Museum für Völkerkunde first, which redistributed 'Kolonialdubletten' to other German museums — so [German officer name] + [any German museum accession] is itself a red-flag pattern.",
        ]
open(os.path.join(ROOT, "COVERAGE.md"), "w", encoding="utf-8").write("\n".join(cov))

# dup suspects: same folded surname+forename initial across entries
sig = defaultdict(list)
for e in all_entries:
    toks = [t for t in re.split(r"[\s,]+", fold(strip_paren(e["name"])).casefold()) if t and t not in ("von","van","de","der","du","le","la","zu","the","of","and","&","co")]
    if len(toks) >= 2: sig[(toks[-1], toks[0][0])].append(e["name"])
dups = {k: v for k, v in sig.items() if len(v) > 1}
if dups:
    print("DUP-SUSPECTS:")
    for k, v in dups.items(): print("  ", v)

print(f"actors={len(actors)} channels={len(channels)} flat_aliases={len(flat_all)}")
print("patch_actors=", len(patch["actors"]), " patch_channels=", len(patch["channels"]))
for sid, fn in flat_map.items():
    n = len(json.load(open(os.path.join(ROOT, 'flat', fn)))["named_actors"])
    print(f"flat/{fn}: {n}")
