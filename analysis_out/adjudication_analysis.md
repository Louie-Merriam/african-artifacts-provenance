# Full-corpus Haiku adjudication — analysis (2026-07-05)

Run: `bm_adjudicate_v2.py`, gate=strict, KB=`redflags_africa_patched.json`, model=claude-haiku-4-5, Message Batches API. 10,458 records adjudicated (of 19,994), **0 model-call errors**, cost ≈ $17.

## Headline verdicts

| category | records | share of adjudicated |
|---|---|---|
| unfair | 3,576 (2,866 high / 710 medium confidence) | 34.2% |
| insufficient_evidence | 4,721 | 45.1% |
| transactional | 1,465 | 14.0% |
| fair | 696 | 6.7% |

Review queue (`out/full_adjudicated_review_queue.jsonl`): 5,041 records, unfair-first, confidence-ranked.

## Haiku vs the rule scorer (band × verdict)

| band | unfair | transactional | fair | insufficient |
|---|---|---|---|---|
| STRONG | 1,707 | 376 | 70 | 827 |
| REVIEW | 1,542 | 604 | 102 | 1,828 |
| low | 327 | 485 | 524 | 2,066 |

Reading: strong agreement at the top (57% of adjudicated STRONGs → unfair); Haiku also *promoted* 327 scorer-low records to unfair (mostly single-actor chains where it supplied the historical context itself); and 827 STRONGs came back insufficient_evidence — the predicted conservative delta on laundered chains, where the rules stack signals but Haiku has no loot quote to cite.

## Laundered test cases (from digitalbenin_and_laundered_test.md)

| reg | via | Haiku verdict |
|---|---|---|
| Af1911,0620.1 aquamanile | W.O. Oldman | **unfair (high)** |
| Af1949,46.161 altar | Dorothy Oldman | **unfair (high)** |
| Af1922,0714.1 arm-cuff | Glendining | **unfair (high)** |
| Af1963,04.1 gong | ex-Webster | **unfair (high)** |
| Af1928,0112.2.a-b anklet | Burney / Ralph Locke | **unfair (high)** — cites Locke's 1897 expedition role |
| Af1954,23.1489 anklet | Wellcome Institute | **unfair (high)** |
| Af1868,1005.4 Maqdala tabot | — | **unfair (high)** |
| Af1896,0512.82 Manhyia armlet | Gold Coast Govt | **unfair (high)** |
| Af1902,0516.25 hair-pin | Fenton & Sons | insufficient (low) |

The old "naive keyword 0/12" cases now come back unfair from the model itself. The two hold-outs are the weakest chains (a hair-pin via Fenton; the single Quaritch manuscript → insufficient) — i.e. Haiku applies the laundering override to court/ritual material but hedges on minor objects, which matches the §3 calibration intent.

## Verdict mix by key actor line

| line | verdict mix |
|---|---|
| Torday (1,179) | 878 unfair / 156 transactional / 145 insufficient |
| Wellcome (1,289) | 835 insufficient / 262 unfair / 178 transactional — the dispersal line alone doesn't convince it; needs object-type or episode co-signal |
| Oldman (257) | 220 unfair |
| Crown Agents (166) | 163 unfair |
| Speedy (134) | 128 unfair |
| Webster (180) | 98 unfair / 75 insufficient |
| Garrard (25) | 25 unfair |
| Partridge (284) | 205 insufficient / 59 unfair — conservative on DC field collections, as it should be |
| Bent (128) | 104 insufficient / 13 unfair |
| Quaritch (1) | insufficient — the classic laundered manuscript; rules flag it, model won't infer without a quote |

Top drivers of unfair verdicts: torday (878), rhodes (275), gold_coast_government (271), wellcome (262), oldman (220), crown_agents (163), speedy (128), henry_wellcome (123), webster (89), beasley (83), niger_coast_protectorate (60), partridge (58).

## Quality issue found & fixed: char-split evidence quotes

310 records (225 of them unfair) returned `evidence_quotes` as single characters — the known v4 bug (single chars trivially pass the substring check). Fixes applied:
1. `bm_adjudicate.py` `validate_quotes` now drops quote fragments < 4 chars (an unfair call with no surviving real quote auto-downgrades).
2. Those 310 records were re-adjudicated under the fixed validator (batch msgbatch_01JZ98XA9aBBMzuzZNKtJJfv, 310/310 ok). Outcome of the re-judgments: 61 unfair / 168 insufficient / 65 fair / 16 transactional — i.e. ~164 formerly unverifiable "unfair" calls were demoted, exactly as the evidence rule demands. Zero sub-4-char quotes remain in the final output; every remaining unfair verdict carries verifiable record quotes.

## Remaining coverage gap (optional top-up)

1,173 scorer STRONG/REVIEW records (23 STRONG + 1,150 REVIEW) never reached Haiku — their band comes from scorer-only signals (episode date-windows, object-type × origin priors, loot language) with no named KB entity. Options: leave them to the human queue (they're in the scorer output), or run them as a broad-gate top-up batch (~$2). The 23 STRONGs are worth it.

## Bottom line

Out of 19,994 BM Africa records: 3,576 model-adjudicated unfair (2,866 high-confidence), every one with verifiable evidence quotes, heavily concentrated in exactly the episodes and dealer chains the expanded registry was built to catch — with sources for every flag in `africa_redflags/SOURCES.md`. Every verdict is a lead for human review, not a determination.
