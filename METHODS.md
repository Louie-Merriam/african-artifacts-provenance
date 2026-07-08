# Detailed methods — pan-African registry build and full-corpus run

*Companion to the overarching-methodology document ("Colonial-looting provenance detector"). That document describes the system's design principles; this one records what was concretely done in this build: sources, protocols, parameters, and the numbers at each step. July 2026.*

## 1. Inputs

The evidence base was the British Museum's own catalogue: `bm_africa_corpus.csv`, 19,994 records harvested via the BM search-results CSV export (per `BM_CSV_EXPORT_FINDINGS.md`), carrying the full acquisition schema (acquisition names in four roles, acquisition notes, curators' comments, find spot, production place, department). Pre-existing assets: the v4 rule scorer and watchlist (71 named-actor aliases, Benin-centric), the `redflags_africa.json` knowledge base (29 actors, 12 channels), and the extractor/adjudicator pipeline.

## 2. Registry construction (broadening beyond Benin)

### 2.1 Structured-registry mining

Three machine-readable provenance registries were mined end-to-end, each with a different access protocol discovered during the work:

- **Open Restitution Africa** — the visible database page is an advocacy directory; the real case corpus was enumerated through the site's WordPress layer (sitemap index + open REST API). All 24 published case studies were read in full; actors and holding institutions were extracted from the case narratives with their episode context. Claimant-side figures (restitution activists, researchers) were explicitly excluded.
- **Proveana (German Lost Art Foundation) and PAESE** — mined as an index: persons and corporate bodies carrying colonial-context occupation tags (*Kolonialdienst, Militär + Sammeltätigkeit, Handel mit Ethnografica, Human Remains*) plus colony tags (DSWA, Kamerun, Togoland, DOA). Entries whose flag rests only on these registry tags are marked `why_flag_basis: "index"` so their weaker evidentiary basis stays visible. PAESE subproject pages supplied richer per-collector documentation (e.g. Strümpell: ~700 objects to Braunschweig from documented "violent military interventions").
- **Digital Benin** — the lost `digitalbenin_actors.json` was rebuilt from source. The listing page is client-rendered, but the site runs on a Sanity CMS with an open query API; all 954 registry entries (784 persons, 167 institutions) were pulled from it and cross-validated against the rendered listing (100% agreement). Raw entries preserved in `digitalbenin_names_raw.json`.

### 2.2 Episode research

Non-Benin looting episodes were researched in parallel streams organized by colonial sphere — British (Maqdala, Asante, Zulu, Omdurman, Great Zimbabwe, Nigeria-beyond-Benin, Uganda/Kenya), German (Herero-Nama and Hornkranz, Maji-Maji/Mkwawa, Cameroon, Togo, the human-remains networks), French/Belgian (Dahomey, Ségou, Madagascar, Samory, Dakar-Djibouti, Congo Free State), and the transnational "tribal art" market (London, Paris, Berlin/Hamburg, Brussels/Antwerp, New York dealers; missionary, estate, and exhibition dispersals). The source hierarchy, in descending weight: museums' own provenance research (BM contested-objects pages, V&A, AfricaMuseum Tervuren provenance articles, Quai Branly's Dakar-Djibouti counter-inquiry, Pitt Rivers, NMS "Baggage and Belonging" object catalogues), repatriation documentation (Charité/Freiburg skull returns, Linden-Museum, SPK provenance volumes), peer-reviewed scholarship (e.g. Watt's BJMH study naming the 1874 Kumasi prize agents), then reputable reporting.

**Inclusion standard:** no name enters the registry without a citable document linking it to looted or coercively acquired material; every entry's `why_flag` states the documented association and that presence is a review signal, not proof. Seeds that failed verification were dropped and logged (Everard im Thurn — no African material found; Fortnum & Mason — no source found; a supposed 1874 Christie's Asante sale — unconfirmed). Living or recently deceased figures were excluded unless documented in published restitution findings; weak celebrity donor lines (the DMNS vigango donors) were excluded outright.

### 2.3 Alias engineering and matching safety

Because the shortlister does word-boundary string matching, aliases were engineered per rules: both name orders generated ("Surname, Forename" ↔ "Forename Surname", with particle handling: *von Pavel, Curt*), ASCII-folded variants for diacritics (Strümpell → Strumpell), parenthetical-stripped forms, and a hard ≥2-token rule. Common names carry only qualified aliases (`context_required` — e.g. Ian Douglas Smith, never bare "Ian Smith"). High-volume entities that would swamp matching were confined to the knowledge base as context and excluded from flat lists (`exclude_flat`: Christy, Franks-adjacent channels, Sotheby's/Christie's, the BM itself, royal-gift phrasing). Result: 221 actors + 90 channels → ~1,190 matchable aliases across six per-source registries, merged with cross-source deduplication.

## 3. Empirical feedback loop (corpus → registry)

Following the handoff's "empirical first" principle, the corpus's structured acquisition-name fields were frequency-analyzed (1,259 distinct names) and annotated against both watchlists. This surfaced how the BM actually records dealer stock — widow/estate donor lines — and four documented aliases were added: Dorothy Oldman (209 records), Mrs Cornelia Mary Speedy (89), Irene Marguerite Beasley (99), and "Wellcome Institute for the History of Medicine" (1,272). High-frequency names with no documentation (Wild, Curle, Macleod, Powell-Cotton, Jeffreys, Plass…) were recorded as verification candidates and deliberately **not** flagged.

## 4. Integration and matching engineering

Deliverables were emitted in the pipeline's native formats: per-source flat alias registries (Digital Benin format, auto-merged), a deduplicating patch into the KB (`redflags_africa_patched.json`: 29→226 actors, 12→96 channels, with 29 patch entries merged into existing rather than duplicated), and `redflags_watchlist_v5.json` (named_actors 71→1,244; →2,932 with the rebuilt Digital Benin file). The scorer was patched to auto-merge *any* `*_actors.json` beside the KB. Matching at this alias volume made per-alias regex infeasible (~26M regex calls per corpus pass); an Aho-Corasick multi-pattern automaton with post-hoc word-boundary checks replaced it (full-corpus pass: ~45 s → ~6 s; adjudicator shortlisting: minutes → 2.5 s), with a fallback to the original matcher when the library is absent.

## 5. Full-corpus run configuration

- **Gate redesign.** The adjudicator's stock shortlist fired on *any* KB table including regions — on an all-Africa corpus that passes 17,779/19,994 (89%), 7,321 of them region-only. The production gate (`--gate strict`) requires an actor, channel, incident, or method match (10,458 records); regions still reach the model as context when something else hits.
- **Batch execution.** The serial loop (per-call connections, 0.2 s sleeps, retry storms on held connections) was replaced with the Anthropic Message Batches API: 10,458 requests in two batches, identical prompts/tool schema to the serial path, half price, ~25 minutes wall-time, 0 call errors, ≈$17. Every verdict streams to disk on collection; re-running the same command resumes (in-flight batches are re-attached, collected batches defer to the stream file).
- **Guardrails.** Verdicts are forced through a JSON tool schema; evidence quotes must be verbatim substrings of the record. A validator hole (single-character "quotes" trivially passing the substring test) was found affecting 310 records; the validator now drops fragments <4 characters and auto-downgrades unfair verdicts with no surviving evidence. The 310 were re-adjudicated: 61 unfair / 168 insufficient / 65 fair / 16 transactional — i.e. ~164 unsupported unfair calls demoted. Zero malformed quotes remain.

## 6. Validation

- **Laundered-case panel** (dealer-chain objects with no loot language, previously 0/12 by keyword): now unfair-high from the model with verbatim quotes (Oldman aquamanile, ex-Webster gong, Wellcome-line anklet, Burney/Locke anklet, Manhyia armlet, Maqdala tabot); the model hedges on the two weakest chains (Quaritch manuscript, Fenton hair-pin → insufficient), matching the calibration intent.
- **Negative control (accidental).** The corpus's "Edo" keyword slice had pulled in 1,108 Asia-department records (Japanese Edo-period material, largely the 1881 William Anderson purchase). The pipeline returned **zero unfair** verdicts on ~1,000 Japanese objects — a corpus-scale false-positive test passed. The contamination itself was documented and the master table given a `dept` column.
- **Cross-system comparison.** Band × verdict cross-tabulation: 57% of adjudicated scorer-STRONGs → unfair; 327 scorer-low records promoted by the model (it supplies historical context records omit); 827 STRONGs → insufficient, the predicted conservative delta on thin laundered chains. Per-actor verdict mixes behaved sanely (Crown Agents 163/166 unfair; Garrard 25/25; Wellcome-line mostly insufficient absent a co-signal; Partridge/Bent field collections mostly hedged).
- **Integrity checks** at each build: JSON validity, alias-hygiene probes (no dangerous bare names in flat lists), join integrity (0 reg-number misses between corpus, scorer, and adjudicator outputs).

## 7. Outputs and geographic analysis

All results were joined into `out/FINAL_bm_africa_provenance_master.csv` (19,994 rows: identifiers, full acquisition text, department, scorer band/score/rules, verdict, confidence, evidence quotes, rationale, matched entities). Final split: 3,576 unfair (2,866 high-confidence) / 4,721 insufficient / 1,465 transactional / 696 fair / 9,536 not shortlisted.

The flow map (`build_flow_map.py` → `artifact_flows_map.html`) aggregates the master table: places parsed from **find spot first** (where the journey to the museum began), production place as fallback; geocoded against a hand-built, auditable gazetteer (~115 entries incl. episode sites: Maqdala, Royal Palace Kumasi, Mushenge) with country-substring fallback — no external geocoding service. Records route origin → documented hub → BM when matched chain entities name a hub firm/museum (Elder Dempster→Liverpool, Trocadéro/Ratton→Paris, Pareyn/Tervuren→Brussels). Display rules: Asia-department rows, UK origins, and non-African origins (Africa bounding box) are excluded and counted in the header; 15,367 records mapped to 88 origin points. Marker size = √count, colour = share unfair; all filtering is client-side.

## 8. Reproducibility

Everything is re-runnable from the folder: `build_registry.py` (registry from per-source files), `bm_flag_v5.py <csv>` (scorer), `bm_adjudicate_v2.py --records … --dry-run` then without (adjudication, resumable), `bm_name_frequency.py freq|shakeout` (corpus analyses), `build_flow_map.py` (map). Documentation: `FINDINGS.md` (results), `africa_redflags/SOURCES.md` (every name → document), `africa_redflags/COVERAGE.md` (per-episode counts, exclusions, gaps), `analysis_out/adjudication_analysis.md` (run analysis).

## 9. Limitations

Registry coverage remains uneven (strong where provenance research exists; Sierra Leone 1898, Aro-level individual takers, Sokoto officer names, Madagascar are thin). Index-derived Proveana/PAESE flags rest on registry tags rather than per-object files. Place data is mostly country/region-granular, and ~3,100 findspot names remain ungeocoded. Model verdicts have been validated against curated cases and internal consistency, not yet benchmarked against institutional ground truth (Digital Benin object status, museums' own contested lists) — that benchmarking, the 1,173-record top-up batch, and human review of the 5,041-record queue are the standing next steps.
