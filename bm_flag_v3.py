#!/usr/bin/env python3
"""
bm_flag_v3.py - multi-path conditional red-flag scorer for British Museum CSV exports.

Improves on v2 in three ways the tests exposed:
  1. MULTI-PATH episodes. An episode is confirmed when a core place term co-occurs with
     ANY corroborator - a second related place term (e.g. Abyssinia + Maqdala), an
     acquisition year in range, loot language, or a palace/channel/military signal.
     Date is one path among several, not the sole gate. Undated objects can still
     confirm via place co-occurrence.
  2. PROVENANCE-ONLY matching. Place/loot/channel terms are matched over acquisition
     fields (notes, names, findspot, curators, culture), NOT the object Description -
     so a print that DEPICTS a looted scene is not mistaken for a looted object.
  3. DISAMBIGUATED 'benin'. Bare 'benin' is a region term only (it also names the
     Republic of Benin / Dahomey); the Benin-1897 episode needs a corroborator.

Still a PRE-FILTER / shortlister producing research leads, not verdicts. The bands
(STRONG / REVIEW / low) decide what a human or the Haiku adjudicator looks at.
Edit redflags_watchlist_v3.json to grow coverage.

Usage:
    python3 bm_flag_v3.py <bm_export.csv> [--kb redflags_watchlist_v3.json] [-o review_queue]

Uses the clean 'Reg number' column (the BM export's 'Museum number' is mangled).
"""
import csv, json, re, sys, argparse, os

def wb(text, kw):
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
    g = lambda k: (o.get(k) or '')
    prov = ' \n '.join(g(k) for k in kb['provenance_fields']).lower()   # provenance/context only
    full = ' \n '.join(str(v) for v in o.values()).lower()             # everything (for object identity)
    type_ = g('Object type').lower()
    findspot = g('Find spot').lower()
    dept = g('Dept')
    year = get_year(g('Acq date'))

    W, M, B = kb['weights'], kb['mitigations'], kb['bands']
    is_dep    = any(t in type_ for t in kb['depiction_types'])
    has_loot  = bool(any_wb(prov, kb['loot_language']))                 # judged on provenance
    is_modern = year is not None and year >= M['modern_year_threshold']
    foreign_dept = bool(re.search(r'Africa, Oceania|Asia|Middle East', dept or '', re.I))
    is_foreign = foreign_dept or any(t in prov for t in kb['foreign_findspot_terms'])
    palace_ctx = bool(re.search(r'\b(palace|royal|oba|emperor|treasury|fortress)\b', prov, re.I))
    dv = [v for v in kb['donation_verbs'] if v in prov]
    mr = any_wb(prov, kb['military_rank'])
    military_ctx = bool(dv) and bool(mr)
    chan = [c for c in kb['colonial_channels'] if c in prov]
    channel_ctx = bool(chan) and is_foreign

    hits, score = [], 0
    def add(rid, w):
        nonlocal score
        hits.append({'rule': rid, 'w': w}); score += w

    # ---- multi-path episodes ----
    for e in kb['episodes']:
        core_hit = any_wb(prov, e['core'])
        region_hit = any_wb(prov, e['region'])
        in_yr = year is not None and e['years'][0] <= year <= e['years'][1]
        path, w = None, 0
        if core_hit:
            if in_yr:
                path, w = 'core+year', W['episode_strong']
            elif has_loot:
                path, w = 'core+loot', W['episode_strong']
            elif (region_hit or palace_ctx or channel_ctx or military_ctx) and (year is None or year <= M['context_year_max']):
                path, w = 'core+context', W['episode_context']
        elif region_hit and in_yr and (has_loot or palace_ctx or channel_ctx):
            path, w = 'region+year+context', W['episode_context']
        if w > 0:
            if is_dep and not has_loot:
                hits.append({'rule': 'suppressed_depiction:' + e['id'], 'w': 0})
            else:
                add('episode:%s[%s]' % (e['id'], path), w)

    # ---- independent signals ----
    if has_loot:
        add('loot_language', W['loot_language'])
    if military_ctx:
        add('military_donor', W['military_donor'])
    if channel_ctx:
        add('colonial_channel', W['colonial_channel'])
    if is_foreign and palace_ctx and (year is None or year <= M['palace_year_max']):
        if not (is_dep and not has_loot):
            add('royal_or_palace_site', W['royal_or_palace_site'])
    if re.search(r'collected during|during the expedition|during the campaign|on the expedition', prov):
        add('expedition_collected', W['expedition_collected'])
    hr = any_wb(full, kb['human_remains'])
    if hr:
        add('human_remains', W['human_remains'])
    sc = any_wb(full, kb['sacred_regalia'])
    if sc and (is_foreign or any(h['rule'].startswith('episode') for h in hits)):
        add('sacred_regalia', W['sacred_regalia'])
    ex = any_wb(prov, kb['excavation'])
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

    band = 'STRONG' if score >= B['strong'] else ('REVIEW' if score >= B['review'] else 'low')
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
    ap.add_argument('--kb', default=os.path.join(os.path.dirname(__file__), 'redflags_watchlist_v3.json'))
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
    print("scored %d objects -> %d STRONG, %d REVIEW, %d low" % (len(results), strong, review, len(results)-strong-review))
    for r in results[:20]:
        print("  [%-6s] %3d  %-18s %-38s %s" % (r['band'], r['score'], r['reg'], r['object'][:38], '; '.join(r['fired'])))

if __name__ == '__main__':
    main()
