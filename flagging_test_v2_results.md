# Flagging test v2 — conditional rules + expanded watchlist

**Date:** 2026-06-27. Rebuilt the scorer per two requests: (1) episodes must be **conditional** (place AND date window, not a bare keyword), and (2) **expand the watchlist**. Re-ran on the original 14 objects plus 8 freshly scraped ones (22 total). Engine + watchlist saved as `bm_flag_v2.py` and `redflags_watchlist_v2.json`; Python output verified to match the live run.

## What changed in the logic

- **Episodes are now `place-alias AND acquisition-year-in-window`.** "Abyssinia" only triggers Maqdala if the object was acquired 1867–1872; "Asante/Manhyia" only in 1873–1901; etc. A drawing that merely *depicts* a place (and carries no loot language) is suppressed.
- **Expanded watchlist:** episodes now include Benin 1897, Maqdala 1868, Asante wars, **Dahomey 1892, Omdurman 1898, Summer Palace 1860, Tibet 1904**; place aliases include **Manhyia, Kumasi, Coomassie, Abomey, Yuanmingyuan**; colonial channels include **Gold Coast Government, Crown Agents, Royal Niger Company, Sudan Government**, etc.
- **"Military donor" now requires a real rank** (general/colonel/captain/expeditionary force…), so the honorific "Sir" / "Earl" no longer fires it. Matching is word-boundary, so "general" no longer matches "generally".
- **Mitigations:** modern acquisitions (≥1960) and depiction objects without loot language are capped low; excavation/seller-gap rules require a foreign context (non-European department or foreign findspot).

## Before / after on the original 14

| Reg | Object | v1 | v2 | Truth | Result |
|---|---|---|---|---|---|
| Af1868,1005.4 | tabot (Maqdala) | 9 | **17 STRONG** | looted | correct, stronger |
| Af1896,0512.82 | armlet, Manhyia Palace | 1 (missed) | **12 STRONG** | looted | **false negative fixed** |
| 1895,0408.6.8 | drawing of Abyssinia | 6 (FP) | **0** | not looted | **FP fixed** |
| Af1893,1111.170 | cross, Ethiopia 1893 | 9 (FP) | **0** | collected | **FP fixed** |
| 1925,0521.152.CR | Wedgwood, Staffordshire | 2 (FP) | **0** | UK domestic | **FP fixed** |
| 1887,0307,I.369 | Wedgwood seal ("Sir") | 4 (FP) | **0** | neutral | **FP fixed** |
| E,4.38 | Dürer print (empty seller) | 2 (FP) | **0** | neutral | **FP fixed** |
| SL,5218.51 | Dürer/Sloane drawing | 3 (FP) | **2 low** | neutral | capped low (depiction) |
| Af1952,13.12 | gold-weight, UAC 1952 | 0 | 0 | transactional | correct |
| 2013,2034.16354 | modern photo | 0 | 0 | modern | correct |
| 1866…/1879… prints, PM.262 banknote, 1894 dial | neutral | 1 | 0 | neutral | correct |

Every false positive removed; the one false negative (Asante loot) now caught.

## Fresh 8 (generalization check — not seen when tuning)

| Reg | Object | Year | v2 | Read |
|---|---|---|---|---|
| (Dahomey) | sword, Dahomey | 1869 | **4 REVIEW** | military donor, but pre-1892-conquest → correctly *review*, not strong |
| Af1951,12.90 | basket, Dahomey | 1951 | 0 | correct |
| 1935…, 1957… | coins, Omdurman | 1935/57 | 0 | acquired outside 1897–1901 → correct |
| OA+.6957 | opium-pipe, "Summer Palace" | none | 0 | **limitation:** no acq date → episode can't confirm (possible miss) |
| Af,A30.2 | photo, "Summer Palace" | 1968 | 0 | modern depiction → correct |
| 1958… ×2 | watch parts ("clock") | 1958 | 0 | correct |

## Honest residual limitations

1. **Date-missing records can't confirm an episode** (the undated opium-pipe). A findspot + loot-language fallback should be added so episode evidence isn't purely date-gated.
2. **`military_donor` still lightly fires** when a real rank word co-occurs with a donation verb (e.g. the Sloane drawing) — the depiction cap keeps it at "low", but on a non-depiction object it could surface a soft false positive. Worth requiring the rank to sit near the donor name.
3. This is still the **rule/shortlist layer**, not the Haiku adjudicator. It decides *what to look at*; verdicts (unfair/transactional/fair/insufficient) and verbatim evidence quotes are the adjudicator's job, which needs the real scripts + a local API key.

## Files
- `redflags_watchlist_v2.json` — the expandable watchlist (episodes, channels, ranks, mitigations, weights). Edit this to grow coverage.
- `bm_flag_v2.py` — the scorer. Run: `python3 bm_flag_v2.py <bm_export.csv> -o review_queue` → writes `review_queue.csv/.jsonl`, sorted by score.
