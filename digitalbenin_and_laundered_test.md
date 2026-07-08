# Digital Benin mine + laundered-case test

## 1. Digital Benin provenance registry — mined

Scraped `digitalbenin.org/provenance`: **954 unique entries** (772 named persons in "Surname, Forename" form, plus auction houses and firms). Expanded to **2,098 alias variants** (added "Forename Surname" reconstructions). Because these are full multi-token names, matches are high-precision.

- A **curated 58-name subset** (auction houses + notable dealers/collectors: Webster, Oldman, Knoedler, Glendining, Parke-Bernet, Fenton, Stevens, Lugard, Gurlitt, Seligmann, Hooper, …) is now in `redflags_watchlist_v4.json`.
- The **full file** (`digitalbenin_actors.json`, ~51 KB) is auto-merged by `bm_flag_v4.py` whenever it sits in the same folder — so dropping it in lifts `named_actors` from 58 to ~2,098 with no code change.

## 2. Laundered-case test — the real measure of the system

The point: objects that are almost certainly 1897 Benin loot but entered the museum *later, through the dealer market*, with **no explicit loot language** in the record. A keyword scorer is blind to these.

Pulled 12 real BM "Benin" objects whose provenance names a watch-listed dealer **and contains no loot word**:

| Reg | Object | Acq year | Via | Naive keyword | v4 rules |
|---|---|---|---|---|---|
| Af1911,0620.1 | aquamanile | 1911 | W.O. Oldman | — | STRONG (11) |
| Af1949,46.161 | altar | 1949 | Dorothy Oldman | — | STRONG (10) |
| Af1979,01.4560/4561 | altar-tusk ×2 | 1949/? | Oldman | — | STRONG (10) |
| Af1922,0714.1 | arm-cuff | 1922 | Glendining & Co | — | STRONG (10) |
| Af1963,04.1 | gong | 1963 | (ex-Webster) | — | STRONG (10) |
| Af1928,0112.2 | anklet | 1928 | Sir Sydney Burney | — | STRONG (10) |
| Af1954,23.1489 | anklet | 1954 | Wellcome Institute | — | STRONG (9) |
| Af1909,0811.9 | armlet | 1909 | Lady Macdonald | — | STRONG (6) |
| Af1902,0516.25 | hair-pin | 1902 | Fenton & Sons | — | REVIEW (5) |
| Af1930,0423.9 / Af1979,01.4450 | armlet ×2 | 1930/? | (Benin court) | — | REVIEW (5) |

**Naive keyword: 0/12. v4: 12/12 (9 STRONG, 3 REVIEW), via dealer-watchlist + Benin object-priors, zero loot language.** This is the date-independent expansion doing exactly its job.

## 3. What this sets up for Haiku (the open question)

These 12 are the cases that actually measure Haiku's *independent* reasoning, because the answer is **not written in the record**. The hypothesis to test on the real run:

The adjudicator's system prompt says *"unfair requires concrete evidence … explicit spoils language. Cite the quote(s)"* and *"do not invent facts."* So Haiku may well return **insufficient_evidence or transactional** for most of these — it has no loot quote to cite and is forbidden from inferring "Benin court object + dealer chain ⇒ 1897 loot." If so, the finding is the reverse of the intuition: on laundered loot, **the rules are more aggressive than Haiku**, and Haiku's real role is conservative validation, not bold inference.

The real Haiku run on these 12 will settle it: if Haiku calls them unfair, it's doing genuine inference; if it says insufficient_evidence, the dealer-chain reasoning lives in the rules, not the model. Either way, that delta is the answer to "how much independent reasoning is Haiku doing."

## Files
- `digitalbenin_actors.json` — full 2,098-alias registry (drop next to the watchlist; auto-merged).
- `laundered_cases.csv` — the 12 no-loot-word dealer-provenance objects, ready for `run_haiku.sh`.
