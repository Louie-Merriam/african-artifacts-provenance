# Handoff — Build a robust pan-African red-flag list (dealers / collectors / actors / channels)

**Goal of the new chat:** produce a comprehensive, *documented* watchlist of the people, firms, auction houses, and institutions that handled looted/coercively-acquired African cultural objects and human remains — across **all** of Africa, not just Benin. Output feeds an existing provenance-flagging pipeline (below). Every name must trace to a source; the list is a **suspicion signal for review, not proof of wrongdoing**.

---

## 1. Why this exists (the gap)

A provenance pipeline flags British Museum objects likely acquired through colonial looting, then a lightweight LLM (Claude Haiku) adjudicates each flagged record. The dealer/collector watchlist is currently **Benin-heavy** because one purpose-built registry (Digital Benin) was mined for ~954 Benin names. **There is no equivalent for Maqdala/Ethiopia, Herero-Nama/Namibia, Asante, Congo, Sokoto, Zulu, Dahomey, Madagascar, etc.** Non-Benin loot is presently caught by episode/region/object-type/loot-language signals, but the *laundered* case — an object whose only red flag is a suspect dealer decades later — is weak outside Benin. This chat closes that gap.

## 2. How the list is used (so you format it right)

Pipeline: `scrape BM records → normalize → KB shortlist (cheap) → Haiku adjudication (evidence-cited) → review queue`.

Two files consume the watchlist:
- **`redflags_africa.json`** — the knowledge base Haiku reads. Tables: `incidents, actors, channels, regions, methods, mitigating_features`. Dealers/collectors go in **`actors`**; firms/auction houses/companies/institutions go in **`channels`**.
  - `actors` entry schema: `{"id","name","aliases":[...],"role","why_flag"}`
  - `channels` entry schema: `{"id","name","aliases":[...],"type","why_flag"}`
  - The shortlister matches any `alias` (word-boundary) in a record's provenance text; a hit advances the record to Haiku, which weighs it against mitigating features and must quote the record.
- **`redflags_watchlist_v4.json`** — a standalone rule scorer's flat `named_actors: [...]` list of alias strings.
- **`digitalbenin_actors.json`** — the Benin model: `{"source","named_actors":[~2,098 alias strings]}`, auto-merged by the scorer. Build one of these **per source you mine** (e.g. `ora_actors.json`, `proveana_actors.json`).

**A watch-listed dealer already overrides a "clean later sale"** in Haiku's prompt (the laundering rule keys on anything under `actors`/`channels`), so every name you add automatically gets that treatment.

## 3. Conventions & principles (do not skip)

- **Alias format:** BM stores names **surname-first**. For each person include both `"Surname, Forename"` **and** `"Forename Surname"`, plus a distinctive 2-token form. **Avoid bare common surnames** ("Ward", "Smith", "Young") — they cause false matches. Prefer full multi-token names.
- **Suspicion, not proof.** These dealers also sold legitimately-acquired material. `why_flag` must say the presence is a flag for review. Calibrate in the text: a *court/ritual object of a looted culture* via a flagged dealer is strong; a trade bead via the same dealer is weak.
- **Verify every name against a source** before adding; cite it in `why_flag` or a companion sources file. Do not invent associations. These are (mostly deceased) historical figures; frame as documented provenance association.
- **Tag by episode/region** where possible (Maqdala, Herero-Nama, Asante, Congo…) so coverage gaps are visible.

## 4. Sources to mine (the actual research)

**Structured / scrapeable (replicate the Digital Benin method — scrape the DOM for name entries, dedupe, format):**
- **Digital Benin — provenance registry** · https://digitalbenin.org/provenance — *Benin only, already mined (~954 names).* Use as the template.
- **Open Restitution Africa — database** · https://openrestitution.africa/database/ — pan-African restitution efforts incl. **human remains**; names holding institutions and actors across the continent. (African Digital Heritage / Andani.Africa.)
- **Proveana (German Lost Art Foundation)** · https://www.proveana.de/en — searchable by **people, corporations, collections, provenance**; has a dedicated **"colonial contexts"** research area (covers Namibia, Cameroon, Tanzania, Benin, etc.). Highest-value structured source for German-colonial dealers/collectors.
- **PAESE — Postcolonial Provenance Research** · https://www.postcolonial-provenance-research.com/en — per-object acquisition circumstances (gift/loot/purchase) for German ethnological collections.
- **The BM's own records (you already have them).** `bm_africa_corpus.csv` (~16k African objects) — the `Acq name`, `Acq notes`, and `Curators Comments` fields *name the dealer/collector chains*. **Frequency-analyze those fields to surface the real recurring names in the BM's African holdings, then verify each against the sources above.** This is the most direct, empirical route and should be step 1.

**Scholarly / reference (extract named figures manually):**
- **Sarr & Savoy, *The Restitution of African Cultural Heritage* (2018)** — foundational; names the acquisition mechanisms and key figures.
- **Dan Hicks, *The Brutish Museums* (2020)** — the Benin network and the broader colonial-collecting logic.
- **AFROMET** (Association for the Return of the Maqdala Ethiopian Treasures) — Maqdala/Ethiopia holders and dispersal.
- **Charité Human Remains Project / German–Namibian repatriation records** — Herero/Nama remains; von Luschan; the Charité and Berlin anthropological collections.
- **Pitt Rivers Museum "Labelling Matters"**, **Horniman** Benin work, **V&A/BM** Ethiopian & Asante provenance pages.
- **Auction archives** (Sotheby's / Christie's / Bonhams "African Art") — provenance chains name the intermediaries.

## 5. Seed list to verify + expand (documented starters, by episode)

Treat as leads to confirm against §4, not as final:
- **Maqdala / Ethiopia (1868):** Richard Rivington Holmes (BM), Capt. Tristram Speedy, Sir Robert Napier; Bernard Quaritch (Ethiopian manuscripts). Holders: BM, V&A, Bodleian, Royal Library Windsor.
- **Herero & Nama / Namibia (1904–08):** Felix von Luschan, Eugen Fischer; the Charité (human remains); Schutztruppe officers.
- **Asante / Ghana (1874/96/1900):** Garrard & Co (crown jeweller, Asante gold), Garnet Wolseley, Robert Baden-Powell.
- **Congo (Free State):** Emil Torday, Herbert Ward, Leo Frobenius.
- **West Africa conduit:** Arnold Ridyard (Elder Dempster steamers → Liverpool).
- **Broad "tribal art" market (pan-African laundering):** W.D. Webster, W.O. Oldman, Augustus Pitt-Rivers, Charles Ratton, K.J. Hewett, William Ohly/Berkeley Galleries, Josef Mueller, Arthur Speyer, Merton Simpson, James Hooper, Everard im Thurn.
- **Nigeria beyond Benin (Sokoto 1903, Aro 1902):** Frederick Lugard; Northern Nigeria Regiment officers.

## 6. Deliverables the new chat should produce

1. **`africa_actors.json`** — merged, de-duplicated, *sourced* registry: each entry `{name, aliases[], role, episode_tags[], region, source, why_flag}`.
2. Per-source registries (`ora_actors.json`, `proveana_actors.json`, …) in the `digitalbenin_actors.json` flat-alias format for the scorer to auto-merge.
3. **Patched `redflags_africa.json`** — new `actors` and `channels` entries.
4. **Patched `redflags_watchlist_v4.json`** — expanded `named_actors`.
5. **`SOURCES.md`** — every name → its documentary basis (so the flags are defensible).
6. A short **coverage report**: names per episode/region, and remaining gaps.

## 7. Method (recommended order)

1. **Empirical first:** frequency-analyze `bm_africa_corpus.csv` provenance fields → ranked list of recurring dealer/collector names actually in the BM's African holdings.
2. **Verify + enrich** each candidate against ORA / Proveana / PAESE / the scholarship; capture the source.
3. **Scrape** the structured registries (ORA, Proveana person/corporation search, Digital Benin as template) for names not surfaced in step 1.
4. **Format** with the alias conventions (§3); tag by episode.
5. **Merge** into the KB + watchlist; write `SOURCES.md` and the coverage report.
6. **Validate:** re-run a shakeout of laundered non-Benin objects (e.g. Maqdala manuscripts via Quaritch, Namibian objects via von Luschan) and confirm they now flag.

## 8. Current state you're inheriting (files already built)

`redflags_africa.json` (20 incidents, 29 actors, 12 channels, 15 regions, 8 methods — pan-African), `redflags_watchlist_v4.json` (21 episodes, 71 named_actors), `digitalbenin_actors.json` (~2,098 Benin aliases), `bm_africa_corpus.csv` / `bm_africa_corpus_objects.csv` (~16–20k African records), `bm_adjudicate.py` + `bm_provenance_extractor.py` (pipeline), `run_haiku.sh`. The laundering-override prompt patch is documented separately.

---

## 9. Kickoff prompt (paste this to start the new chat)

> I'm building a **robust, documented red-flag watchlist of dealers, collectors, auction houses, and institutions that handled looted or coercively-acquired African cultural objects and human remains — across all of Africa** — for a British Museum provenance-flagging pipeline (flags → Claude Haiku adjudication). Benin is already covered via the Digital Benin registry (~954 names); I need parity for Maqdala/Ethiopia, Herero-Nama/Namibia, Asante, Congo, Sokoto, Zulu, Dahomey, Madagascar, and the broad "tribal art" market. See HANDOFF_african_redflag_list.md for the schema, conventions, sources, seed list, and method. **Start by frequency-analyzing the provenance fields of bm_africa_corpus.csv to surface the dealer/collector names actually present in the BM's African holdings, then we'll verify each against Open Restitution Africa, Proveana, PAESE, and the restitution scholarship.** Every name must be source-backed; the list is a suspicion signal for review, not proof.
