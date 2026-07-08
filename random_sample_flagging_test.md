# Random-sample flagging test — British Museum

**Date:** 2026-06-27 · 14 objects scraped live via the BM CSV export and scored.

## Important caveat on what was actually run

The validated detector (`redflags_africa.json` knowledge base + `bm_adjudicate.py` Haiku adjudicator) is **not in the connected Drive folder** — only the legacy keyword scorer `redflag_rules.json` is. Real Haiku also can't run in this sandbox (no egress to api.anthropic.com). So this test ran the **legacy keyword scorer only** (14 weighted regex rules), which the handoff already marks as *superseded*. Read the results as a test of the *cheap pre-filter layer*, not the full pipeline. They are still informative — they show exactly the failure modes the KB+Haiku layer was built to fix.

## The sample

Randomly drawn: 6 from colonial-context queries (Maqdala / Asante / Ethiopia) + 8 from neutral queries (barometer / Wedgwood / sundial / Dürer) to test false positives.

| # | Reg number | Object | Dept | Acq date | Score | Rules fired | Truth | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 1895,0408.6.8 | drawing of Abyssinia (Zander sketchbook) | Prints & Drawings | 1895 | 6 | maqdala_1868, era | not looted (art-market purchase) | **FALSE POSITIVE** |
| 2 | Af1868,1005.4 | tabot (sacred altar tablet) | AOA | 1868 | 9 | maqdala_1868, presented_by_officer, era | **Maqdala loot** (Northcote; "taken from the fortress of Tewodros") | **CORRECT** |
| 3 | Af1896,0512.82 | armlet, findspot Manhyia Palace | AOA | 1896 | 1 | era | **almost certainly Asante loot** (1896 Kumasi; Gold Coast Govt) | **FALSE NEGATIVE** |
| 4 | Af1952,13.12 | gold-weight, Ghana | AOA | 1952 | 0 | — | transactional (UAC agent, c.1900) | correct (not flagged) |
| 5 | Af1893,1111.170 | cross pendant, Ethiopia | AOA | 1893 | 9 | maqdala_1868, presented_by_officer, era | collected/purchased (Bent 1893; Franks gift) | **FALSE POSITIVE** |
| 6 | 2013,2034.16354 | digital photo of Tiya stelae | AOA | 2013 | 0 | — | modern donation | correct (true negative) |
| 7 | 1866,1114.841 | satirical print | Prints & Drawings | 1866 | 1 | era | neutral | correct |
| 8 | 1879,0510.123 | print | Prints & Drawings | 1879 | 1 | era | neutral | correct |
| 9 | 1925,0521.152.CR | Wedgwood kiln-furniture, Staffordshire | BEP | 1925 | 2 | excavated_and_exported | neutral (UK domestic dig) | **FALSE POSITIVE (low)** |
| 10 | 1887,0307,I.369 | Wedgwood seal | BEP | 1887 | 4 | presented_by_officer, era | neutral | **FALSE POSITIVE (borderline)** |
| 11 | PM.262 | banknote | Money & Medals | 1932 | 0 | — | neutral | correct |
| 12 | 1894,1211.7 | magnetic dial | BEP | 1894 | 1 | era | neutral | correct |
| 13 | E,4.38 | Dürer print | Prints & Drawings | <1810 | 2 | no_named_seller | neutral | **FALSE POSITIVE (low)** |
| 14 | SL,5218.51 | Dürer drawing (Sloane) | Prints & Drawings | 1753 | 3 | presented_by_officer | neutral (Sir Hans Sloane founding gift) | **FALSE POSITIVE (borderline)** |

## What the test shows

**The one unambiguous loot case scored highest (Tabot, 9).** When the record literally says "taken from the fortress of Tewodros … Abyssinian Campaign," the scorer nails it. The pipeline's true-positive instinct is sound.

**But the keyword layer is noisy in both directions:**

*False positives from blunt keywords.* "abyssinia" appearing anywhere fires the full-weight `maqdala_1868` rule — so a European artist's *sketchbook of Ethiopian scenery* (#1) and an 1893 *collected* cross (#5, where "Abyssinia" is only in a cross-reference to a different object) both score 9, same as real loot. And `presented_by_officer` fires on the honorific "Sir" — catching Sir Hans Sloane (#14) and Sir A.W. Franks (#5), neither a military officer. `excavated_and_exported` fired on a Staffordshire pottery dig (#9).

*A false negative that matters most.* The Manhyia Palace armlet (#3) — Asante royal regalia, findspot the Asante king's palace, taken 1896, donated by the colonial Gold Coast Government — scored just **1**, because the `asante` rule only matches the literal strings "asante/ashanti/kumasi/kumase," none of which appear in the record. A genuinely looted object slipped through.

## Why this is exactly the case for the KB+Haiku layer

This is a clean demonstration of why the project moved past keyword scoring. The fixes the failures point to are already the project's design:

1. **Mitigating features** (modern arm's-length purchase, "depicts" vs "taken from," collector vs officer) would pull #1, #5, #9, #13, #14 back down — the handoff's "keep fair/transactional honest" goal.
2. **Richer place/actor/channel signals** — "Manhyia Palace," "Gold Coast Government," "Prempeh," 1896 Kumasi — would catch #3. The literal-keyword approach can't.
3. **Disambiguating honorifics from military rank**, and **requiring a foreign findspot** for the excavation/seller-gap rules, removes most of the low-grade neutral noise.

Net: scraping is solved and the data carries the right signals, but **detection accuracy depends entirely on the KB+Haiku layer that isn't available in this session.** To run the real thing, the validated scripts (`bm_adjudicate.py`, `bm_provenance_extractor.py`, `redflags_africa.json`, `run_haiku.sh`) need to be in a connected folder, and Haiku run locally per the handoff.
