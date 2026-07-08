# BM "Download results" CSV export — test findings

**Date:** 2026-06-27 · Tested live through the connected Chrome browser against britishmuseum.org/collection.

## Verdict: the bulk CSV export works and is the right primary harvest route.

It returns the **entire result set of a search in a single CSV**, with the full
acquisition schema, **uncapped** at the 1,000-row limit that constrains the
separate Museum Data Service. This should replace per-object page scraping wherever a
search can express the slice you want.

## How it actually works

- **Endpoint:** `GET https://www.britishmuseum.org/api/_download?<same search params>&view=grid&sort=object_name__asc&page=1`
  — i.e. take any `/collection/search?...` query and hit the `/api/_download` path with the same params.
- **The `page` parameter is ignored.** `page=1`, `2`, `3`, `4` all return the identical file containing the *whole* result set. You do **not** paginate the export.
- **Trigger it as a same-origin `fetch()` with an `Accept: text/csv` header**, not as a browser navigation/download. The on-page "Download results" button navigates to the endpoint and the browser logged **HTTP 503** every time; the same URL fetched in-page returns **HTTP 200** with the full CSV body.
- **First request for an uncached query is slow** — the server generates the CSV on demand and the first call can exceed 45s / 503. **Retry and it serves from cache instantly.** (Same "fire it again, it'll come back" behaviour the handoff already notes for heavy object pages.)

## Cap / completeness test

| Query | Search UI count | Records in CSV | Bytes | Notes |
|---|---|---|---|---|
| Maqdala | 270 | **270** | 0.5 MB | exact match |
| Asante | 3,728 | **3,728** | 4.1 MB | cached → 59 ms |
| Ethiopia | 3,910 | **3,910** | 6.6 MB | 1st call timed out (uncached); retry 68 ms, exact match |

Record count equals the search result count exactly in every case → **no truncation, no 1,000 cap.** Confirmed complete up to ~3,900 rows; the only real constraint is first-call generation latency, which a retry resolves.

## Schema — 47 columns, acquisition data populated

The export carries the full acquisition block the detector needs, populated (not just headers):

`Find spot`, `Acq name (acq)`, `Acq name (finding)`, `Acq name (excavator)`,
`Acq name (previous)`, `Acq date`, `Acq notes (acq)`, `Acq notes (exc)`,
`Dept`, `Reg number`, `Object type`, `Culture`, `Production date/place`,
`Curators Comments`, `Bib references`, plus more (47 total).

Real rows pulled in the test (Maqdala query):

- `Reg number` Af1868,1001.4 — `Acq notes (acq)`: *"Looted by Richard Holmes at Maqdala (13 April 1868)…"* · `Find spot`: Maqdala
- `Reg number` Af1939,09.17 — `Acq notes (acq)`: *"Collected by Capt. T.C. Speedy in Abyssinia during British Expedition, 1867-68"* · `Acq name (acq)`: Donated by Ida Perrin

Both hit existing KB signals (R.R. Holmes actor; expedition-participant / "collected during expedition" method).

### Data quirk to handle in the extractor
The **`Museum number`** column is mangled — values come through as `No: Optional[Af1868,1001.4]` (a leaked `Optional[...]` serialization wrapper). **Use the clean `Reg number` column instead** for the registration/slug. (Slug = `E_` + Reg number with commas/periods/spaces → hyphens, per the handoff.)

## Recommended harvest strategy

1. **Drive everything off `/api/_download`.** For each slice you care about, build the `/collection/search` query, swap to `/api/_download`, fetch same-origin with `Accept: text/csv`, retry-on-timeout, parse.
2. **Chunk by Department + Acquisition-date range** (the search supports both) to keep each export in the safe few-thousand-row band and to make first-call generation fast. Suggested first slices: Africa/Oceania/Americas dept × acquisition windows around 1868 (Maqdala), 1874/1896/1900 (Asante), 1897 (Benin), plus Egypt/Sudan and Dahomey windows.
3. **Feed CSVs straight into `bm_provenance_extractor.py` via the `csv` adapter** — but point it at `Reg number`, not `Museum number`.
4. Per-object page scraping is now only needed for fields the CSV omits or for spot-validation, not for bulk harvest.

## Open items this did *not* settle
- Upper ceiling above ~3,900 rows (e.g. a 20k–50k query): not tested because uncached generation blows the 45s tool timeout. Chunking by dept/date keeps you well under this anyway.
- Whether `view`/`sort` params affect the row set (they shouldn't — only ordering).
