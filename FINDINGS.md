# Pan-African provenance red-flag project — final findings

*2026-07-05 · covers the registry build, the full-corpus run, and the geographic analysis. All flags are documented suspicion signals for human review, not determinations of wrongdoing; the dealers listed also handled legitimately acquired material.*

## 1. What was built

The watchlist went from Benin-only (~954 Digital Benin names + 71 curated aliases) to a **sourced pan-African registry: 221 actors and 90 channels, ~1,190 matchable aliases**, every entry traceable to a document in `africa_redflags/SOURCES.md`. Sources mined: all 24 Open Restitution Africa case studies (via its WordPress API), Proveana and PAESE (the German colonial-contexts indexes), museum provenance projects (BM contested-objects pages, V&A, AfricaMuseum Tervuren, Quai Branly counter-inquiries, Pitt Rivers, NMS "Baggage and Belonging"), repatriation records (Charité, Freiburg, Linden-Museum, SPK), episode scholarship (Watt's prize-agents article, Sarr-Savoy), and market research (London/Paris/Berlin/Hamburg/Brussels/New York dealers and dispersals). `digitalbenin_actors.json` was also rebuilt from source (954 entries via Digital Benin's Sanity API, → 1,788 aliases).

Episode coverage now spans Maqdala 1868, Asante 1874/1896/1900, Zulu 1879, Omdurman 1898, Great Zimbabwe, Sokoto/Aro/Ife, Bunyoro and Kenya, Hornkranz 1893 and the Herero-Nama genocide, Maji-Maji/Mkwawa, Cameroon (Duala 1884, Bangwa, Nso 1902, Grassfields), Togo, Dahomey 1892, Ségou 1890, Madagascar 1895-97, Dakar-Djibouti 1931-33, and the Congo Free State.

**Structural findings worth keeping:**
- **The laundering chain has a repeating shape:** [extraction] → [soldier/missionary/shipping/exhibition conduit] → [specialist dealer] → [collector-museum] → [20th-c. dispersal] → [clean-looking accession]. Chains that *start* at a dispersal-stage name are truncated.
- **German pattern:** the 1889 Bundesrat resolution routed everything officers appropriated to the Berlin Museum für Völkerkunde first — so [German officer name] + [any German museum accession] is itself a red flag.
- **Widow/estate donor lines are how the BM records dealer stock:** Dorothy Oldman (209 records), Mrs Cornelia Mary Speedy (89), Irene Beasley (99), "Wellcome Institute for the History of Medicine" (1,272). The corpus itself supplied these aliases.
- **Calibration exclusions matter:** Christy, Franks, Sotheby's/Christie's and the BM itself are too generic to match on; common names carry qualified aliases only; unverifiable seeds (Everard im Thurn, Fortnum & Mason) were dropped, and weak high-profile donor lines (Hackman/Linson vigango) excluded.

## 2. What the full run found (19,994 BM Africa records)

Rule scorer (`bm_flag_v5.py`, aliases 71→2,932): **3,003 STRONG / 5,226 REVIEW**. Haiku adjudication (`bm_adjudicate_v2.py`, strict gate, Batches API — 10,458 records, ~25 min, ≈$17):

| verdict | records |
|---|---|
| **unfair** | **3,576** (2,866 high-confidence) |
| insufficient_evidence | 4,721 |
| transactional | 1,465 |
| fair | 696 |

- **The laundered-loot problem is solved at the model level too:** the dealer-chain Benin objects that naive keyword matching scored 0/12 on now come back unfair-high with verbatim record quotes (Oldman aquamanile, ex-Webster gong, Wellcome-line anklet, Burney/Locke anklet…). Haiku hedges exactly where it should: the lone Quaritch manuscript and a Fenton hair-pin → insufficient.
- **Rules and model cross-validate:** 57% of adjudicated STRONGs → unfair; Haiku promoted 327 scorer-low records (supplying historical context the record omits, e.g. Manhyia Palace + Gold Coast Govt + 1896 ⇒ sack of Kumasi); 827 STRONGs → insufficient (the model won't infer without evidence — the conservative delta predicted in `digitalbenin_and_laundered_test.md`).
- **Per-actor calibration is sane:** Crown Agents 163/166 unfair, Garrard 25/25, Speedy 128/134, Torday 878/1,179; Wellcome mostly insufficient without a co-signal; Partridge and Bent field collections mostly hedged.
- **Geography (see `out/artifact_flows_map.html`):** Maqdala 64/64 unfair, Royal Palace Kumasi 141/147, Benin City 678/1,055, Mushenge (Kuba capital, Torday) 270/387; DR Congo is the reddest large region. Documented market hubs visible in the BM's own chains: Paris, Brussels/Antwerp, Liverpool.

## 3. Quality controls that fired

- **Evidence-quote bug:** 310 records returned single-character quotes; `validate_quotes` patched (≥4 chars, unfair-with-no-evidence auto-downgrades), 310 re-adjudicated → ~164 demoted. Zero garbage quotes remain; every unfair verdict carries verifiable quotes.
- **"Edo" harvest homonym:** 1,108 Asia-dept records (Japanese Edo-period material, largely the William Anderson 1881 purchase) rode in on the corpus's "Edo" keyword slice. The pipeline was not fooled — **0 unfair verdicts on ~1,000 Japanese objects**, a free negative control. Master CSV now carries a `dept` column; next harvest should constrain slices by department.
- **Regions-gate lesson:** on an all-Africa corpus, region aliases shortlist 89% of records; the strict gate (actors/channels/incidents/methods) cut the Haiku queue from 17,779 to 10,458 with regions kept as context.

## 4. Deliverables

`africa_redflags/` (registry + flat lists + patches + SOURCES.md + COVERAGE.md) · `digitalbenin_actors.json` + `digitalbenin_names_raw.json` · `redflags_watchlist_v5.json` · `redflags_africa_patched.json` · `bm_flag_v5.py` (auto-merges any `*_actors.json`, fast matcher) · `bm_adjudicate_v2.py` (strict gate, Batches API, incremental/resume) · `out/FINAL_bm_africa_provenance_master.csv` (all 19,994 records: provenance, band, verdict, evidence, rationale, entities) · `out/full_adjudicated_review_queue.jsonl` (5,041, ranked) · `out/artifact_flows_map.html` + `build_flow_map.py` · `analysis_out/` (frequency table, shakeout, adjudication analysis).

## 5. Open items

1. **1,173 scorer-flagged records never reached Haiku** (23 STRONG + 1,150 REVIEW; flagged by date-window/object-prior/loot-language only) — a ~$2 broad-gate top-up batch.
2. **Verification candidates** from the corpus frequency table (Wild, Curle, Macleod, Powell-Cotton, Jeffreys, Plass…) — high-frequency names deliberately NOT flagged without documentation.
3. **Research gaps:** Sierra Leone 1898 takers, Aro 1901-02 individuals, Sokoto 1903 officer names (watch the Caliphate's announced Red List), Madagascar depth; bulk sources unmined (Atlas der Abwesenheit's ~40k Cameroon objects, other NMS regimental PDFs, BM biography term pages, Waterfield & King).
4. **Human review** of the 5,041-record queue — the pipeline's output is leads with evidence, not conclusions.
