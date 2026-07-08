# African Artifact Provenance — a computational red-flag pipeline for the British Museum's Africa collection

A pipeline that reads museum object records and produces an **evidence-cited, human-reviewable shortlist of objects likely acquired through colonial looting or coercion**. Applied to 19,994 British Museum Africa records, it adjudicated 10,458 and returned **3,576 unfair verdicts (2,866 high-confidence), each backed by verbatim quotes from the museum's own records** — for ≈ $17 of model inference and ~25 minutes of wall time.

> **Read this first — suspicion, not proof.** Every "red flag" in this repository is a *documented provenance association that warrants review*, not a determination of wrongdoing. The dealers and collectors on the watchlist also handled legitimately acquired material; every model verdict is a research lead for human and institutional review, not a legal claim about any object or person. Every watchlist name traces to a published source in [`africa_redflags/SOURCES.md`](africa_redflags/SOURCES.md).

## Headline results

| verdict (Claude Haiku, evidence-cited) | records |
|---|---|
| unfair | 3,576 (2,866 high-confidence) |
| insufficient evidence | 4,721 |
| transactional | 1,465 |
| fair | 696 |
| not shortlisted (no watchlist entity in record) | 9,536 |

Selected findings (details in [`FINDINGS.md`](FINDINGS.md) and [`analysis_out/results_interpretation.md`](analysis_out/results_interpretation.md)):

- Only **21% of unfair verdicts rest on explicit seizure language** in the museum's records; 79% required chain/context inference — the measured gap between keyword search and this method.
- **Records with royal/palace findspots are 92% unfair** (Manhyia Palace, the Oba's palace, Maqdala 64/64).
- The **laundering tail is a century long**: a quarter of dated Benin-1897 unfair objects entered the museum more than 57 years after the sack (latest: 1992).
- Object types form the predicted gradient: Benin plaques 90% unfair → goldweights 24% → coins 3%.
- A ~1,000-record accidental negative control (Japanese Edo-period objects pulled in by a keyword homonym) yielded **zero** unfair verdicts.
- Sensitivity of the unfair count to the evidentiary standard: 741 (explicit-language only) → 2,212 → 2,866 → 3,576 (presumption standard); see §12 of the interpretation doc.

**Interactive map:** [`out/artifact_flows_map.html`](out/artifact_flows_map.html) — origins sized by object count, colored by unfair share, arcs routed through documented dealer/museum hubs to the BM. Download and open in a browser (or serve via GitHub Pages).

## Repository map

| path | what it is |
|---|---|
| `bm_provenance_extractor.py` | BM CSV → normalized provenance records + rule flags |
| `bm_flag_v5.py` (v2–v4 kept for history) | deterministic weighted rule scorer (STRONG/REVIEW/low); auto-merges every `*_actors.json` beside the KB; Aho–Corasick fast matcher |
| `bm_adjudicate.py` / `bm_adjudicate_v2.py` | LLM adjudication. v2 = production runner: strict shortlist gate, Anthropic Message Batches API, incremental writes + resume, quote-validation guardrails |
| `redflags_africa_patched.json` | knowledge base: 226 actors, 96 channels, incidents/regions/methods/mitigations |
| `redflags_watchlist_v5.json` | scorer watchlist (named_actors 71 → 1,244) |
| `africa_redflags/` | the pan-African registry build: per-source files, flat alias lists, patches, **SOURCES.md** (every name → document), **COVERAGE.md** (episodes, exclusions, gaps) |
| `digitalbenin_actors.json` / `digitalbenin_names_raw.json` | Digital Benin provenance registry (954 entries via its public API), expanded to 1,788 aliases |
| `bm_africa_corpus.csv` | the 19,994-record corpus (BM Collection Online export — see licensing) |
| `out/FINAL_bm_africa_provenance_master.csv` | **the master result**: every record + provenance + scorer band + verdict + evidence quotes + rationale + matched entities |
| `out/full_adjudicated.jsonl.gz`, `out/full_adjudicated_review_queue.jsonl.gz` | full adjudication output; ranked review queue (5,041) |
| `out/artifact_flows_map.html`, `build_flow_map.py` | the interactive map and its generator (editable gazetteer at top) |
| `FINDINGS.md`, `METHODS.md`, `CITATIONS.md` | results summary; detailed build methods; citation apparatus |
| `analysis_out/` | frequency analysis, shakeout report, adjudication analysis, interpretation (+ robustness §12), nine worked validation cases |
| `HANDOFF_african_redflag_list.md`, `BM_CSV_EXPORT_FINDINGS.md`, other `.md` | project working documents and test logs |

## Reproduce

```bash
pip install anthropic pyahocorasick          # pyahocorasick optional (100x faster matching)

# 1. rule scorer over the corpus (no API key needed)
python3 bm_flag_v5.py bm_africa_corpus.csv -o out/review_queue

# 2. extractor -> records
python3 bm_provenance_extractor.py csv bm_africa_corpus.csv --rules redflag_rules.json -o analysis_out/full_records

# 3. adjudication (needs ANTHROPIC_API_KEY; --dry-run first shows counts + cost, ~$17 batch)
python3 bm_adjudicate_v2.py --records analysis_out/full_records.jsonl -o out/full_adjudicated --dry-run
python3 bm_adjudicate_v2.py --records analysis_out/full_records.jsonl -o out/full_adjudicated

# 4. map
python3 build_flow_map.py

# analyses
python3 bm_name_frequency.py freq && python3 bm_name_frequency.py shakeout
```

The adjudicator resumes if interrupted (re-run the same command); `--gate broad` restores the wider shortlist; `--retry-errors` redoes failed calls.

## Method in one paragraph

A citation-backed knowledge base encodes *how* colonial objects were taken: episodes with date windows, named actors and market channels (mined from Digital Benin, Open Restitution Africa, Proveana/PAESE, museum provenance research, repatriation records, and scholarship), seizure-method language, object-type priors, and mitigating features. A deterministic shortlister matches ~2,900 alias strings (word-bounded, provenance fields only — never object descriptions) and advances a record only on an actor/channel/incident/method hit; dates never gate, so laundered late arrivals still surface. Claude Haiku then adjudicates each shortlisted record against only the flags it matched, returning unfair / transactional / fair / insufficient_evidence with verbatim evidence quotes — enforced by a validator that strips non-verbatim quotes and downgrades unsupported unfair verdicts. Full detail: [`METHODS.md`](METHODS.md).

## Data licensing & attribution

- **Code** (all `.py`, `.sh`): MIT License (see `LICENSE`).
- **British Museum-derived data** (`bm_africa_corpus*.csv`, all files under `out/` and `analysis_out/` containing record text): derived from British Museum Collection Online, **© The Trustees of the British Museum, CC BY-NC-SA 4.0**. These files are shared under the same license (non-commercial, share-alike, with attribution) and are *adapted* (normalized, annotated with computed flags and model verdicts).
- **Registry attributions**: Digital Benin (MARKK, digitalbenin.org); Open Restitution Africa (CC BY 4.0, openrestitution.africa); Proveana (German Lost Art Foundation); PAESE (Lower Saxony). Every actor/channel entry cites its documentary basis in `africa_redflags/SOURCES.md`.
- Model verdicts and analyses are research outputs of this project and inherit the BM data license where they embed record text.

## Citation

If you use this work, please cite the repository and the underlying registries (Digital Benin; Open Restitution Africa; Proveana/PAESE), and see `CITATIONS.md` for the full scholarly apparatus.
