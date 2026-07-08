#!/usr/bin/env python3
"""
bm_flag_v4.py - date-independent, broader red-flag scorer for BM CSV exports.

What changed from v3 (per the "too date-gated" critique):
  * named_actors: a known loot dealer/officer (Webster, Oldman, Pitt-Rivers, Moor,
    Holmes, ...) in the provenance flags the object IN ANY YEAR. This catches the
    laundered case - e.g. a Benin plaque bought from W.D. Webster in 1925 or 1965.
  * object-type x origin priors: a Benin brass plaque, an Ethiopian tabot, Asante
    gold regalia, etc. flag on identity+origin regardless of acquisition date.
  * standalone punitive_expedition method (fires without needing a donor verb).
  * date is now a confidence BOOSTER, not a gate; episodes confirm on
    core-place + any corroborator.
  * the modern / depiction mitigations do NOT suppress actor / prior / loot /
    method / human-remains hits, so late laundered loot still surfaces.
  * a numismatic guard: a coin/medal OF a place is not loot unless there is loot
    language or a named actor.

Still a shortlist/pre-filter producing research leads (STRONG / REVIEW / low),
not verdicts. Edit redflags_watchlist_v5.json to grow coverage.

Usage:
    python3 bm_flag_v4.py <bm_export.csv> [--kb redflags_watchlist_v5.json] [-o review_queue]
"""
import csv, json, re, argparse, os

def wb(t, k): return re.search(r'\b' + re.escape(k) + r'\b', t, re.I) is not None
def any_wb(t, ks): return [k for k in ks if wb(t, k)]

# fast multi-pattern matcher for the (large) named_actors list; falls back to any_wb
try:
    import ahocorasick as _ac
except ImportError:
    _ac = None

def build_actor_matcher(names):
    if _ac is None:
        return lambda t: any_wb(t, names)
    A = _ac.Automaton()
    for n in {x.lower() for x in names if x.strip()}:
        A.add_word(n, n)
    A.make_automaton()
    def match(t):
        hits = set()
        for end, n in A.iter(t):
            s = end - len(n) + 1
            b = t[s - 1] if s > 0 else ' '
            c = t[end + 1] if end + 1 < len(t) else ' '
            if not (b.isalnum() or b == '_') and not (c.isalnum() or c == '_'):
                hits.add(n)
        return sorted(hits)
    return match
def get_year(s):
    m = re.search(r'\b(1[5-9]\d\d|20\d\d)\b', s or ''); return int(m.group(1)) if m else None

def score_row(o, kb):
    g = lambda k: (o.get(k) or '')
    prov = ' \n '.join(g(k) for k in kb['provenance_fields']).lower()
    full = ' \n '.join(str(v) for v in o.values()).lower()
    type_ = g('Object type').lower(); dept = g('Dept'); year = get_year(g('Acq date'))
    W, M, B = kb['weights'], kb['mitigations'], kb['bands']

    is_dep = any(t in type_ for t in kb['depiction_types'])
    is_num = any(t in type_ for t in kb['numismatic_types'])
    has_loot = bool(any_wb(prov, kb['loot_language']))
    method_hit = any_wb(prov, kb['methods'])
    actor_hit = kb['_actor_match'](prov) if '_actor_match' in kb else any_wb(prov, kb['named_actors'])
    is_modern = year is not None and year >= M['modern_year_threshold']
    foreign_dept = bool(re.search(r'Africa, Oceania|Asia|Middle East', dept or '', re.I))
    is_foreign = foreign_dept or any(t in prov for t in kb['foreign_findspot_terms'])
    palace_ctx = bool(re.search(r'\b(palace|royal|oba|emperor|treasury|fortress|asantehene)\b', prov, re.I))
    dv = [v for v in kb['donation_verbs'] if v in prov]
    mr = any_wb(prov, kb['military_rank'])
    military_ctx = bool(dv) and bool(mr)
    chan = [c for c in kb['colonial_channels'] if c in prov]
    channel_ctx = bool(chan) and is_foreign

    hits, score = [], 0
    def add(rid, w):
        nonlocal score; hits.append((rid, w)); score += w
    prior_fired = False

    for e in kb['episodes']:
        core_hit = any_wb(prov, e['core']); region_hit = any_wb(prov, e['region'])
        in_yr = year is not None and e['years'][0] <= year <= e['years'][1]
        prior_hit = any(p in full for p in e.get('priors', [])) and (bool(region_hit) or bool(core_hit))
        path, w = None, 0
        if core_hit and (in_yr or region_hit or has_loot or palace_ctx or channel_ctx or military_ctx or prior_hit):
            path = 'core+year' if in_yr else ('core+loot' if has_loot else ('core+prior' if prior_hit else 'core+context'))
            w = W['episode_strong'] if (in_yr or has_loot) else (W['episode_prior'] if prior_hit else W['episode_context'])
        elif prior_hit:
            path, w = 'origin_prior', W['origin_prior']                 # DATE-INDEPENDENT
        elif region_hit and in_yr and (has_loot or palace_ctx or channel_ctx):
            path, w = 'region+year', W['region_year']
        # numismatic guard
        if w > 0 and is_num and not has_loot and not actor_hit and path != 'core+year':
            hits.append(('suppressed_numismatic:' + e['id'], 0)); w = 0
        if w > 0:
            if is_dep and not has_loot:
                hits.append(('suppressed_depiction:' + e['id'], 0))
            else:
                add('episode:%s[%s]' % (e['id'], path), w)
                if path in ('origin_prior', 'core+prior'):
                    prior_fired = True

    if actor_hit:    add('named_actor:' + actor_hit[0], W['named_actor'])   # DATE-INDEPENDENT
    if has_loot:     add('loot_language', W['loot_language'])
    if method_hit and not is_dep: add('punitive_expedition', W['punitive_expedition'])
    if military_ctx: add('military_donor', W['military_donor'])
    if channel_ctx:  add('colonial_channel', W['colonial_channel'])
    if is_foreign and palace_ctx and (year is None or year <= M['palace_year_max']):
        if not (is_dep and not has_loot):
            add('royal_or_palace_site', W['royal_or_palace_site'])
    if re.search(r'collected during|during the expedition|during the campaign|on the expedition', prov):
        add('expedition_collected', W['expedition_collected'])
    hr = any_wb(full, kb['human_remains'])
    if hr: add('human_remains', W['human_remains'])
    sc = any_wb(full, kb['sacred_regalia'])
    if sc and (is_foreign or any(r.startswith('episode') for r, _ in hits)):
        add('sacred_regalia', W['sacred_regalia'])

    protected = bool(actor_hit) or prior_fired or has_loot or bool(hr) or bool(method_hit)
    mit = []
    if is_modern and not protected:
        if score > M['modern_cap']: score = M['modern_cap']
        mit.append('modern_transactional')
    if is_dep and not has_loot and score > M['depiction_cap']:
        score = M['depiction_cap']; mit.append('depiction_object')

    band = 'STRONG' if score >= B['strong'] else ('REVIEW' if score >= B['review'] else 'low')
    return {'reg': g('Reg number'), 'object': g('Object type'), 'dept': dept,
            'acq_date': g('Acq date'), 'year': year, 'findspot': g('Find spot'),
            'score': score, 'band': band,
            'fired': ['%s(%d)' % (r, w) for r, w in hits if w > 0], 'mitigations': mit}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_path')
    ap.add_argument('--kb', default=os.path.join(os.path.dirname(__file__), 'redflags_watchlist_v5.json'))
    ap.add_argument('-o', '--out', default='review_queue')
    a = ap.parse_args()
    kb = json.load(open(a.kb, encoding='utf-8'))
    # auto-merge EVERY per-source actor registry (*_actors.json) beside the watchlist
    # (digitalbenin_actors.json, africa_all_actors.json, ora_actors.json, ...)
    import glob as _glob
    kbdir = os.path.dirname(os.path.abspath(a.kb))
    for extra in sorted(_glob.glob(os.path.join(kbdir, '*_actors.json'))):
        db = json.load(open(extra, encoding='utf-8'))
        names = db.get('named_actors', [])
        if not names: continue
        merged = list(dict.fromkeys(kb['named_actors'] + names))
        print('merged %d aliases from %s (named_actors now %d)'
              % (len(names), os.path.basename(extra), len(merged)))
        kb['named_actors'] = merged
    kb['_actor_match'] = build_actor_matcher(kb['named_actors'])
    rows = list(csv.DictReader(open(a.csv_path, newline='', encoding='utf-8-sig')))
    res = sorted((score_row(r, kb) for r in rows), key=lambda r: -r['score'])
    with open(a.out + '.jsonl', 'w', encoding='utf-8') as f:
        for r in res: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(a.out + '.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['reg', 'band', 'score', 'object', 'acq_date', 'findspot', 'fired_rules', 'mitigations'])
        for r in res: w.writerow([r['reg'], r['band'], r['score'], r['object'], r['acq_date'], r['findspot'], '; '.join(r['fired']), '; '.join(r['mitigations'])])
    strong = sum(1 for r in res if r['band'] == 'STRONG'); review = sum(1 for r in res if r['band'] == 'REVIEW')
    print('scored %d -> %d STRONG, %d REVIEW, %d low' % (len(res), strong, review, len(res)-strong-review))
    for r in res[:20]:
        print('  [%-6s] %3d  %-18s %-30s %s' % (r['band'], r['score'], r['reg'], r['object'][:30], '; '.join(r['fired'])))

if __name__ == '__main__':
    main()
