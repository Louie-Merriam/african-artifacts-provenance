# Running the full pipeline with real Haiku — bundle

This bundle runs the real `bm_adjudicate.py` against Claude Haiku and shows how the
model's judgment differs from the deterministic stub.

## Files

| File | Role | Source |
|---|---|---|
| `bm_provenance_extractor.py` | scrape-CSV → normalized records (+ coarse flags) | you already have it |
| `bm_adjudicate.py` | shortlist → Haiku adjudication → review queue | you already have it |
| `redflag_rules.json` | the extractor's coarse keyword rules | recreated this session |
| `redflags_africa.json` | **the knowledge base Haiku reasons over** | **reconstructed this session** from the v3 watchlist + the actors/channels named in the handoff. Swap in your original validated KB if you have it. |
| `run_haiku.sh` | one-command runner | new |
| `sample_bm_export.csv` | 6 real scraped objects to test on | this session |

Put all of these in one folder (the two `.py` files alongside the rest).

## Run it

```bash
export ANTHROPIC_API_KEY=sk-ant-...            # your key, on your machine
RECORDS_CSV=sample_bm_export.csv bash run_haiku.sh
```

Outputs land in `out/`: `haiku.csv` (full adjudication) and
`haiku_review_queue.jsonl` (unfair + transactional, highest-confidence first).
To run on more data, export any search from the BM site's CSV download and point
`RECORDS_CSV` at it.

## What to look for — mock vs Haiku on the sample

I ran the pipeline here with the deterministic `--mock` stand-in (no key needed).
It labeled **all five** shortlisted objects `transactional` — including the
Maqdala **tabot**, whose record says *"taken from the fortress of Emperor Tewodros
II at Maqdala during the Abyssinian Campaign."* The stub missed it because its
keyword check looks for the literal phrase "taken during".

When you run real Haiku, the interesting question is how many of these it
**re-classifies** and what it **quotes**. Expected divergences:

- **Af1868,1005.4 (tabot)** — mock: transactional → Haiku should say **unfair**, quoting "taken from the fortress … at Maqdala".
- **Af1896,0512.82 (armlet, Manhyia Palace, Gold Coast Government, 1896)** — mock: transactional → Haiku plausibly **unfair** (palace seizure + colonial channel), or a high-confidence review.
- **1895,0408.6.8 (Zander drawing of Abyssinia, purchased 1895)** — mock: transactional → Haiku should pull toward **fair/insufficient** (it depicts the place, an arm's-length purchase).
- **Af1893,1111.170 (cross, collected by Bent 1893)** and **Af1952,13.12 (trade gold-weight)** — likely **transactional/fair** in both.

That delta — re-classifications plus verbatim evidence quotes — is the actual
reasoning Haiku contributes on top of the rule layer.

## Notes
- The adjudicator only sends Haiku records that the shortlister matched, so most
  records never cost a call. `insufficient_evidence` is an allowed, expected verdict.
- Code-side guardrails still apply: any evidence quote that isn't a real substring
  of the record is dropped, and an `unfair` call left with no surviving quote is
  auto-downgraded to `insufficient_evidence`.
- The KB here is a reconstruction. Treat the first real run as a smoke test of the
  *machinery*, not a validated accuracy measurement.
