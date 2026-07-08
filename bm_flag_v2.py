#!/usr/bin/env python3
"""
bm_flag_v2.py - conditional red-flag scorer for British Museum CSV exports.

Improves on the legacy keyword scorer (redflag_rules.json) in two ways the test exposed:
  1. CONDITIONAL episodes: a place alias only counts as a looting signal when the
     acquisition YEAR falls in that episode's window (e.g. Abyssinia AND 1867-1872),
     and depiction objects (prints/drawings/photos) that merely show the place are
     suppressed unless loot language is present.
  2. EXPANDED + disambiguated watchlist: more episodes/places/channels, and
     'military donor' requires a real rank token, not the honorific 'Sir'.

This is a cheap PRE-FILTER / shortlister, not a verdict. Outputs are research leads
for human (or Haiku) adjudication. Edit redflags_watchlist_v2.json to grow coverage.

Usage:
    python3 bm_flag_v2.py <bm_export.csv> [--kb redflags_watchlist_v2.json] [-o review_queue]

Column mapping targets the BM 'Download results' CSV schema. Note the BM export's
'Museum number' column is mangled (e.g. "No: Optional[Af1868,1001.4]"); this script
uses the clean 'Reg number' column instead.
"""
import csv, json, re, sys, argparse, os

def wb(text, kw):
    """Word-boundary, case-insensitive membership test."""
    return re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE) is not None

def any_wb(text, kws):
    return [k for k in kws if wb(text, k)]

def get_year(s):
    m = re.search(r'\b(1[5-9]\d\d|20\d\d)\b', s or '')
    return int(m.group(1)) if m else None

def load_kb(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def score_row(o, kb):
    """o: dict keyed by BM CSV column names. Returns a result dict."""
    g = lambda k: (o.get(k) or '')
    notes   = (g('Acq notes (acq)') + ' ' + g('Acq notes (exc)')).lower()
    text    = ' \n '.join(str(v) for v in o.values()).lower()
    type_   = g('Object type').lower()
    findspot= g('Find spot').lower()
    dept    = g('Dept')
    year    = get_year(g('Acq date'))

    W = kb['weights']; M = kb['mitigations']
    is_dep   = any(t in type_ for t in kb['depiction_types'])
    loot_hit = any_wb(notes + ' ' + text, kb['loot_language'])
    has_loot = bool(loot_hit)
    is_modern= year is not None and year >= M['modern_year_threshold']
    foreign_dept = bool(re.search(r'Africa, Oceania|Asia|Middle East', dept or '', re.I))
    is_foreign = foreign_dept or any(t in findspot for t in kb['foreign_findspot_terms'])

    hits, score = [], 0
    def add(rid, w):
        nonlocal score
        hits.append({'rule': rid, 'w': w}); score += w

    # R1 - episode confirmed: place alias AND year-in-window (depiction-without-loot suppressed)
    for e in kb['episodes']:
        pl = [p for p in e['place'] if wb(text, p)]
        if pl and year is not None and e['years'][0] <= year <= e['years'][1]:
            if is_dep and not has_loot:
                hits.append({'rule': 'suppressed_depiction:' + e['id'], 'w': 0})
            else:
                add('episode:' + e['id'], W['episode'])

    # R2 - explicit loot language
    if has_loot:
        add('loot_language', W['loot_language'])

    # R3 - military donor: donation verb AND real rank (not honorific 'Sir')
    dv = [v for v in kb['donation_verbs'] if v in text]
    mr = any_wb(text, kb['military_rank'])
    if dv and mr:
        add('military_donor', W['military_donor'])

    # R4 - colonial channel + foreign context
    ch = [c for c in kb['colonial_channels'] if c in text]
    if ch and is_foreign:
        add('colonial_channel', W['colonial_channel'])

    # R5 - royal / palace seat, foreign, pre-1925
    if is_foreign and re.search(r'\b(palace|royal|oba|emperor|treasury|fortress)\b', findspot + ' ' + notes, re.I) \
       and (year is None or year <= 1925):
        if not (is_dep and not has_loot):
            add('royal_or_palace_site', W['royal_or_palace_site'])

    # R6 - collected during an expedition/campaign
    if re.search(r'collected during|during the expedition|during the campaign|on the expedition', notes + ' ' + text):
        add('expedition_collected', W['expedition_collected'])

    # R7 - human remains
    hr = any_wb(text, kb['human_remains'])
    if hr:
        add('human_remains', W['human_remains'])

    # R8 - sacred/regalia + (episode or foreign)
    sc = any_wb(text, kb['sacred_regalia'])
    if sc and (is_foreign or any(h['rule'].startswith('episode') for h in hits)):
        add('sacred_regalia', W['sacred_regalia'])

    # R9 - excavated + foreign department
    ex = any_wb(notes + ' ' + findspot, kb['excavation'])
    if ex and foreign_dept:
        add('excavated_foreign', W['excavated_foreign'])

    # ---- mitigations ----
    mit = []
    if is_modern and not has_loot and not hr:
        if score > M['modern_cap']:
            score = M['modern_cap']
        mit.append('modern_transactional')
    if is_dep and not has_loot and score > M['depiction_cap']:
        score = M['depiction_cap']
        mit.append('depiction_object')

    b = kb['bands']
    band = 'STRONG' if score >= b['strong'] else ('REVIEW' if score >= b['review'] else 'low')
    return {
        'reg': g('Reg number'), 'object': g('Object type'), 'dept': dept,
        'acq_date': g('Acq date'), 'year': year, 'findspot': g('Find spot'),
        'score': score, 'band': band,
        'fired': [h['rule'] + '(' + str(h['w']) + ')' for h in hits if h['w'] > 0],
        'mitigations': mit,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_path')
    ap.add_argument('--kb', default=os.path.join(os.path.dirname(__file__), 'redflags_watchlist_v2.json'))
    ap.add_argument('-o', '--out', default='review_queue')
    args = ap.parse_args()

    kb = load_kb(args.kb)
    with open(args.csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    results = [score_row(r, kb) for r in rows]
    results.sort(key=lambda r: -r['score'])

    with open(args.out + '.jsonl', 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(args.out + '.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['reg', 'band', 'score', 'object', 'dept', 'acq_date', 'findspot', 'fired_rules', 'mitigations'])
        for r in results:
            w.writerow([r['reg'], r['band'], r['score'], r['object'], r['dept'], r['acq_date'],
                        r['findspot'], '; '.join(r['fired']), '; '.join(r['mitigations'])])

    strong = sum(1 for r in results if r['band'] == 'STRONG')
    review = sum(1 for r in results if r['band'] == 'REVIEW')
    print(f"scored {len(results)} objects -> {strong} STRONG, {review} REVIEW, "
          f"{len(results)-strong-review} low")
    print(f"wrote {args.out}.jsonl and {args.out}.csv")
    for r in results[:15]:
        print(f"  [{r['band']:6}] {r['score']:>3}  {r['reg']:<18} {r['object'][:40]:<40} {'; '.join(r['fired'])}")

if __name__ == '__main__':
    main()
