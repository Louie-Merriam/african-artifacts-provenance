# Shakeout report — expanded pan-African watchlist vs corpus

- corpus rows: 19994
- records hit by EXISTING v4 named_actors: **389**
- records hit by v4 + africa registry: **4196**  (**+3807 newly flagged**)

## Top 40 africa-registry aliases actually firing in this corpus

- wellcome institute: 1272
- wellcome institute for the history of medicine: 1272
- emil torday: 1161
- cecil rhodes: 282
- charles partridge: 273
- gold coast government: 271
- henry wellcome: 240
- dorothy oldman: 209
- sir henry wellcome: 172
- crown agents for the colonies: 166
- crown agents: 166
- william ockelford oldman: 161
- irene marguerite beasley: 99
- william downing webster: 89
- wellcome historical medical museum: 89
- mrs cornelia mary speedy: 89
- cornelia mary speedy: 89
- james theodore bent: 84
- captain speedy: 69
- tristram c s speedy: 63
- tristram speedy: 60
- captain tristram speedy: 60
- richard rivington holmes: 36
- r & s garrard & co: 24
- garrard & co: 24
- india office: 19
- napier of magdala: 18
- kasai company: 17
- british empire exhibition, wembley: 17
- robert napier: 16
- sale of loot: 15
- musee de l'homme: 13
- prize committee: 12
- sydney burney: 11
- musee de l'homme, paris: 11
- fenton & sons: 11
- leo frobenius: 10
- harry beasley: 8
- eva cutter: 7
- j.c. stevens: 6

## Expected laundered/non-Benin test cases

- 'Quaritch' appears in provenance of 1 records
- 'Speedy' appears in provenance of 134 records
- 'Secretary of State for India' appears in provenance of 1 records
- 'Torday' appears in provenance of 1179 records
- 'Wellcome' appears in provenance of 1289 records
- 'Garrard' appears in provenance of 25 records
- 'Crown Agents' appears in provenance of 166 records
- 'Luschan' appears in provenance of 0 records
- 'Umlauff' appears in provenance of 1 records
- 'Oldman' appears in provenance of 257 records
- 'Webster' appears in provenance of 213 records
- 'Ridyard' appears in provenance of 0 records
- 'Elder Dempster' appears in provenance of 1 records
- 'prize sale' appears in provenance of 0 records
- 'Frobenius' appears in provenance of 13 records
- 'Roscoe' appears in provenance of 3 records
- 'Hollis' appears in provenance of 2 records
- 'Meinertzhagen' appears in provenance of 0 records
- 'Partridge' appears in provenance of 278 records
- 'Wolseley' appears in provenance of 26 records
- 'Baden-Powell' appears in provenance of 1 records
- 'Kitchener' appears in provenance of 1 records

## 20 sample newly-flagged records

- Af,A154.44 (photographic print (object name); album ) ← william downing webster
- Af,A154.45 (photographic print (object name); album ) ← william downing webster
- Af,A154.30 (photographic print (object name); album ) ← william downing webster
- Af,A154.40 (photographic print (object name); album ) ← william downing webster
- Af,A154.20 (photographic print (object name); album ) ← william downing webster
- Af,A154.23 (photographic print (object name); album ) ← william downing webster
- Af,A154.8 (photographic print (object name); album ) ← william downing webster
- Af,A154.34 (photographic print (object name); album ) ← william downing webster
- Af,A154.39 (photographic print (object name); album ) ← william downing webster
- Af,A154.35 (photographic print (object name); album ) ← william downing webster
- Af,A154.63 (photographic print (object name); album ) ← william downing webster
- Af,A154.17 (photographic print (object name); album ) ← william downing webster
- Af,A154.6 (photographic print (object name); album ) ← william downing webster
- Af,A154.16 (photographic print (object name); album ) ← william downing webster
- Af,A154.37 (photographic print (object name); album ) ← william downing webster
- Af,A154.36 (photographic print (object name); album ) ← william downing webster
- Af,A154.7 (photographic print (object name); album ) ← william downing webster
- Af,A154.3 (photographic print (object name); album ) ← william downing webster
- Af,A154.21 (photographic print (object name); album ) ← william downing webster
- Af,A154.19 (photographic print (object name); album ) ← william downing webster
## Volume calibration (named_actors matching, full corpus)

| configuration | records hit |
|---|---|
| existing v4 named_actors (71 aliases) | 389 |
| + africa registry, full (1,189 aliases) | 4,196 (+3,807) |
| + africa registry excluding the Wellcome-Institute and Torday donor lines | 1,804 (+1,415) |

The two documented high-volume lines drive over half the new hits: the Wellcome Institute donor line (1,272 records — the documented WHMM dispersal channel) and Emil Torday (1,161 records — his own BM field collection). Both are legitimate review categories under Sarr-Savoy logic (dispersal-masking and asymmetric-power expedition collecting), but they behave like the Christy problem: consider a reduced Haiku weight or an episode/object-type co-signal requirement for these two names rather than removal.

Full-scorer result (bm_flag_v5.py, v5 watchlist + africa aliases auto-merged): 2,480 STRONG / 4,284 REVIEW / 13,230 low of 19,994 records.

## High-frequency BM acquisition names NOT yet in any registry (verification candidates — do NOT flag without documentation, per handoff §3)

William Anderson (680), Robert Powley Wild (628, Gold Coast), Norman Hardy (535), Mrs Celia Barclay (326), Frank Jolles (326, Zulu material, modern scholar), Jean Brown (315, East Africa), E M Andrews (281), Alexander T Curle (245, Somaliland colonial officer), Miss M Best (239), Miss Olive Macleod (166, Lake Chad expedition 1910-11), H S Job (155), Sir William Gwynne-Evans (148), Major P H G Powell-Cotton (110) + Miss Antoinette Powell-Cotton (60) (Quex Park expeditions), Mrs Margaret Plass (115, tribal-art market donor), Hermann Justus Braunholtz (120, BM keeper), Dr S F Nadel (77, colonial anthropologist), Major W A C Cockburn (72), M D W Jeffreys (64, colonial administrator Nigeria/Cameroon). Also present but deliberately uncovered: Henry Christy (238), Sir A W Franks (267), Christie's (95) — see COVERAGE.md exclusions; and Secretary of State for Foreign Affairs (168) which the existing KB covers as the Foreign Office channel.

## Integration notes

- redflags_watchlist_v5.json = v4 with named_actors 71 -> 1,244 (africa aliases merged).
- redflags_africa_patched.json = KB with actors 29 -> 226, channels 12 -> 96 (23 actors / 6 channels merged into existing entries rather than duplicated).
- bm_flag_v5.py = v4 scorer + auto-merge of EVERY *_actors.json beside the KB (digitalbenin_actors.json, africa_all_actors.json, ...) + fast multi-pattern actor matching (pip install pyahocorasick; falls back to the old loop without it). NOTE: digitalbenin_actors.json (~2,098 Benin aliases per the handoff) is NOT present in this folder — restore it for full Benin coverage.
- africa_all_actors.json placed in the folder root for the auto-merge.

## Digital Benin registry rebuilt (2026-07-04)

digitalbenin_actors.json was missing and has been rebuilt from source: all 954 registry entries (784 persons, 167 institutions) pulled from Digital Benin's public Sanity CMS query API and cross-validated against the rendered /provenance listing (100% agreement). Raw entries preserved in digitalbenin_names_raw.json. Expanded to 1,788 alias variants (surname-first + forename-first + ASCII-folded + particle variants, e.g. 'Luschan, Felix Ritter von' -> 'Felix von Luschan').

Full-scorer result with BOTH registries auto-merged (named_actors 71 -> 2,932):
| run | STRONG | REVIEW | low |
|---|---|---|---|
| v5 + africa only | 2,480 | 4,284 | 13,230 |
| v5 + africa + digitalbenin | 3,003 | 5,226 | 11,765 |

Haiku queue if adjudicating STRONG+REVIEW = 8,229 records ≈ $27 standard / $14 batch at the estimate in full_run_scope_estimate.md. (_corpus_part*.csv / rq_p*.csv in analysis_out/ are chunked-run artifacts; safe to delete.)

## On dealer lists and guilt-by-association (design note)

A watch-listed dealer handled legitimate material too — the list encodes *documented association with looted material*, not a verdict on every object. The pipeline operationalizes this: an alias hit only shortlists a record; the adjudicator must quote the record's own evidence and weigh mitigating features, and calibration guidance (handoff §3) treats a court/ritual object of a looted culture via a flagged dealer as strong, a trade bead via the same dealer as weak. Every why_flag in the registry says explicitly that presence is a review signal, not proof.
