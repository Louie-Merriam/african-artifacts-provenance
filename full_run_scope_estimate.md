# Full production run — scope & cost estimate

## Measured batch sizes (real counts, from the BM CSV export)

| Slice (keyword) | Records | KB coverage |
|---|---|---|
| Benin | 2,904 | strong |
| Asante | 3,728 | strong |
| Ethiopia (incl. Maqdala 270) | 3,910 | strong |
| Dahomey | 734 | strong |
| Omdurman / Sudan | 355 | moderate |
| **Core-African subtotal** | **~11,600 raw (~11,000 unique after overlap)** | |

The whole **Africa/Oceania/Americas department** is far larger — its CSV export timed out (>45 s to generate), which by itself signals tens of thousands+; the exact figure still needs measuring (I'd chunk it by acquisition-date windows to pull it).

## Cost per Haiku call

- Pricing (looked up): Haiku 4.5 = **$1 / M input tok, $5 / M output tok**; batch API halves both.
- Per record: ~1,500 input tok (system prompt + record + matched KB entries) + ~350 output tok.
- **≈ $0.0033 / call standard, ≈ $0.0016 / call with the batch API.**
- Only **shortlisted** records cost a call. In targeted region batches the shortlist rate is high (our tests: 5/6 and 11/12 ≈ **~85%**). Across a whole mixed department it's lower (~25–35%, since much Oceania/Americas material names no KB entity).

## Three scopes

**A. Core African episodes (recommended first run).**
~11,000 records → ~9,300 Haiku calls → **≈ $31 standard / ≈ $15 batch.**
Scraping: ~5 CSV exports (trivial). Haiku time: a few hours serial, or well under an hour via the batch API. This is the high-confidence, low-cost slice where the KB is validated.

**B. Whole Africa/Oceania/Americas department.**
Total = *to be measured* (call it N). At ~30% shortlist: ~0.30 × N calls.
- If N ≈ 100,000 → ~30,000 calls → **≈ $99 / $50 batch.**
- If N ≈ 300,000 → ~90,000 calls → **≈ $300 / $150 batch.**
Scraping N via the browser export, chunked by date windows, is a multi-hour job but feasible. Recall is trustworthy for the African material, thin for Oceania/Americas until the KB grows.

**C. Whole museum (~2M+ online records).**
Not recommended via this pipeline: scraping millions through the browser export is impractical, most records never shortlist, and recall outside the covered regions is weak. If ever needed, the Museum Data Service bulk download is the right tool, not page-by-page scraping.

## Recommendation

Run **A** first. It's ~$15–31 of Haiku, a few hours, and covers exactly the material the flags + Haiku are validated on — after the three stress tests, confidence there is high. Use it as the real-world shakedown (and to catch the known issues at scale: the character-split quote bug and the leaky loot-word filter). Then measure and expand to **B** region by region, growing the KB (Egypt, India, China, Pacific) before trusting those slices.

## What I'd need from you to launch A
- Your okay to scrape the ~5 batch CSVs and deliver one combined records file (it'll be a few MB → saved to your machine).
- You run it locally on your key (batch API strongly recommended at this volume to halve cost and avoid rate limits).
- Outputs are **research leads for human review**, not verdicts — same framing as the whole project.
