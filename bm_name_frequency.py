#!/usr/bin/env python3
"""Handoff §7 step 1 + shakeout.

step freq    : frequency-analyze the structured Acq-name fields of bm_africa_corpus.csv,
               rank recurring dealer/collector names, annotate coverage
               (existing v4 named_actors vs new africa registry aliases).
step shakeout: word-boundary match v4 named_actors alone vs v4 + africa flat aliases
               over the provenance fields; report newly flagged records and
               verify the expected laundered non-Benin test cases.
Outputs into analysis_out/.
"""
import csv, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "analysis_out")
os.makedirs(OUT, exist_ok=True)
CORPUS = os.path.join(HERE, "bm_africa_corpus.csv")
AFRICA_FLAT = os.path.join(HERE, "africa_redflags", "flat", "africa_all_actors.json")
V4 = os.path.join(HERE, "redflags_watchlist_v4.json")

PROV_FIELDS = ["Acq name (acq)", "Acq name (previous)", "Acq name (excavator)",
               "Acq notes (acq)", "Acq notes (exc)", "Curators Comments"]
NAME_FIELDS = PROV_FIELDS[:3]

def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def load_rows():
    with open(CORPUS, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

import ahocorasick

def wb_automaton(aliases):
    """Aho-Corasick automaton over casefolded aliases; word-boundary check at match time."""
    A = ahocorasick.Automaton()
    for a in {fold(x).casefold().strip() for x in aliases if x.strip()}:
        A.add_word(a, a)
    A.make_automaton()
    return A

def wb_findall(A, lowtext):
    hits = set()
    for end, a in A.iter(lowtext):
        start = end - len(a) + 1
        before = lowtext[start - 1] if start > 0 else " "
        after = lowtext[end + 1] if end + 1 < len(lowtext) else " "
        if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
            hits.add(a)
    return hits

def prov_text(row):
    return fold(" | ".join(row.get(f) or "" for f in PROV_FIELDS))

def step_freq():
    rows = load_rows()
    v4 = json.load(open(V4, encoding="utf-8"))["named_actors"]
    africa = json.load(open(AFRICA_FLAT, encoding="utf-8"))["named_actors"]
    v4f = {fold(a).casefold() for a in v4}
    aff = {fold(a).casefold() for a in africa}

    cnt, roles, sample = Counter(), defaultdict(Counter), {}
    for row in rows:
        seen = set()
        for f in NAME_FIELDS:
            val = (row.get(f) or "").strip()
            if not val: continue
            for part in re.split(r"\s*;\s*", val):
                m = re.match(r"^([^:]{2,40}):\s*(.+)$", part.strip())
                if m: rel, name = m.group(1).strip(), m.group(2).strip()
                else: rel, name = "(none)", part.strip()
                name = re.sub(r"\s+", " ", name).strip(" .")
                if not name or len(name) < 3: continue
                key = fold(name).casefold()
                if key in seen: continue
                seen.add(key)
                cnt[name if name in cnt else min([n for n in cnt if fold(n).casefold() == key], key=len, default=name)] = 0  # noop keep first spelling
        # simpler recount below
    # recount cleanly (two-pass to canonicalize spellings)
    canon = {}
    for row in rows:
        for f in NAME_FIELDS:
            val = (row.get(f) or "").strip()
            if not val: continue
            for part in re.split(r"\s*;\s*", val):
                m = re.match(r"^([^:]{2,40}):\s*(.+)$", part.strip())
                rel, name = (m.group(1).strip(), m.group(2).strip()) if m else ("(none)", part.strip())
                name = re.sub(r"\s+", " ", name).strip(" .")
                if not name or len(name) < 3: continue
                key = fold(name).casefold()
                canon.setdefault(key, name)
    cnt, roles = Counter(), defaultdict(Counter)
    rowhits = defaultdict(set)
    for i, row in enumerate(rows):
        per_row = set()
        for f in NAME_FIELDS:
            val = (row.get(f) or "").strip()
            if not val: continue
            for part in re.split(r"\s*;\s*", val):
                m = re.match(r"^([^:]{2,40}):\s*(.+)$", part.strip())
                rel, name = (m.group(1).strip(), m.group(2).strip()) if m else ("(none)", part.strip())
                name = re.sub(r"\s+", " ", name).strip(" .")
                if not name or len(name) < 3: continue
                key = fold(name).casefold()
                per_row.add(key)
                roles[key][rel] += 1
        for key in per_row:
            cnt[key] += 1
            if len(rowhits[key]) < 3: rowhits[key].add(rows[i].get("Reg number", ""))
    def covered(key, aliasset):
        if key in aliasset: return "exact"
        for a in aliasset:
            if len(a) >= 8 and (a in key or key in a): return "partial"
        return ""
    with open(os.path.join(OUT, "bm_corpus_name_frequency.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "acq_name", "records", "relations", "in_v4_watchlist", "in_africa_registry", "sample_regs"])
        for rank, (key, n) in enumerate(cnt.most_common(), 1):
            rel = "; ".join(f"{r}×{c}" for r, c in roles[key].most_common(3))
            w.writerow([rank, canon[key], n, rel, covered(key, v4f), covered(key, aff), " ".join(sorted(rowhits[key]))])
    top = cnt.most_common(60)
    print(f"rows={len(rows)}  distinct acq names={len(cnt)}")
    print("top 60 recurring acquisition names (records | v4? | africa? | name):")
    for key, n in top:
        print(f"{n:>5}  {covered(key, v4f) or '-':7} {covered(key, aff) or '-':7}  {canon[key]}")

def step_shakeout():
    rows = load_rows()
    texts = [prov_text(row) for row in rows]
    v4 = json.load(open(V4, encoding="utf-8"))["named_actors"]
    africa = json.load(open(AFRICA_FLAT, encoding="utf-8"))["named_actors"]
    A_v4, A_af = wb_automaton(v4), wb_automaton(africa)
    base, expanded, newly = 0, 0, []
    alias_hits = Counter()
    for row, t in zip(rows, texts):
        lt = t.casefold()
        h4 = bool(wb_findall(A_v4, lt))
        m = wb_findall(A_af, lt)
        if h4: base += 1
        if h4 or m: expanded += 1
        if m and not h4:
            newly.append((row.get("Reg number", ""), sorted(m)[:4],
                          (row.get("Object type", "") or "")[:40]))
        for x in m: alias_hits[x] += 1
    lines = ["# Shakeout report — expanded pan-African watchlist vs corpus\n",
             f"- corpus rows: {len(rows)}",
             f"- records hit by EXISTING v4 named_actors: **{base}**",
             f"- records hit by v4 + africa registry: **{expanded}**  (**+{expanded-base} newly flagged**)",
             "\n## Top 40 africa-registry aliases actually firing in this corpus\n"]
    for a, n in alias_hits.most_common(40):
        lines.append(f"- {a}: {n}")
    lines.append("\n## Expected laundered/non-Benin test cases\n")
    lowtexts = [t.casefold() for t in texts]
    for probe in ["Quaritch", "Speedy", "Secretary of State for India", "Torday", "Wellcome",
                  "Garrard", "Crown Agents", "Luschan", "Umlauff", "Oldman", "Webster",
                  "Ridyard", "Elder Dempster", "prize sale", "Frobenius", "Roscoe", "Hollis",
                  "Meinertzhagen", "Partridge", "Wolseley", "Baden-Powell", "Kitchener"]:
        rx = re.compile(r"(?<!\w)" + re.escape(probe.casefold()) + r"(?!\w)")
        n = sum(1 for t in lowtexts if rx.search(t))
        lines.append(f"- '{probe}' appears in provenance of {n} records")
    lines.append("\n## 20 sample newly-flagged records\n")
    for reg, m, ot in newly[:20]:
        lines.append(f"- {reg} ({ot}) ← {', '.join(m)}")
    open(os.path.join(OUT, "shakeout_report.md"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:12]))
    print(f"... full report: analysis_out/shakeout_report.md  (newly flagged: {len(newly)})")

if __name__ == "__main__":
    {"freq": step_freq, "shakeout": step_shakeout}[sys.argv[1]]()
