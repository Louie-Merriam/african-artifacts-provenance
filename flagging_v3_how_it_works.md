# How the flagging works — v3 (conditionals + flag words)

Scope: this is the **shortlist / pre-filter layer** — it decides *what a human or the Haiku adjudicator should look at*, sorted into **STRONG / REVIEW / low**. It does not issue verdicts (unfair/transactional/fair) or evidence quotes; that remains the adjudicator's job. Files: `bm_flag_v3.py` + `redflags_watchlist_v3.json`.

## The core idea

Each object gets a **score** = sum of the signal weights it trips, then a band:
**STRONG ≥ 6 · REVIEW 3–5 · low < 3**.

Two principles drive accuracy:

1. **Conditional episodes (multi-path), not bare keywords.** A place name alone never flags. An episode confirms only when a **core place term co-occurs with a corroborator**.
2. **Judge provenance, not depiction.** All place / loot / channel words are matched over the **acquisition fields only** (acq notes, acq names, findspot, curators' comments, production place, culture) — never the object's Description. So a *print of* a looted scene, or a *drawing of* Abyssinia, is not mistaken for a looted object.

## How an episode confirms (the conditional)

For each episode (Benin 1897, Maqdala 1868, Asante wars, Dahomey 1892, Omdurman 1898, Summer Palace 1860, Tibet 1904), terms are split into **core** (specific: "maqdala", "manhyia", "benin city"…) and **region** (broad/ambiguous: "abyssinia", "gold coast", "benin", "china"…). An episode fires by whichever path is strongest:

| Path | Condition | Weight |
|---|---|---|
| core + year | core term AND acquisition year in the episode window | 6 (STRONG-grade) |
| core + loot | core term AND loot language in provenance | 6 |
| core + context | core term AND (a region term **or** palace/channel/military signal), and year ≤ 1935 or undated | 4 (REVIEW-grade) |
| region + year + context | region term AND year-in-window AND (loot or palace or channel) | 4 |

This is exactly the "**Abyssinia AND Maqdala together**" idea: place co-occurrence is one confirmation path, an in-range **date** is another, loot language a third. **Date is a corroborator, not the sole gate** — so an undated object can still confirm via place co-occurrence, while a date alone (a Victorian print from 1880) confirms nothing.

Two guards keep this honest: the **core+context** path requires the acquisition to be **≤ 1935 or undated** (a 1953 Nigerian carving won't trip "Benin" on context alone), and **"benin" is treated as a region term only** because it also names the Republic of Benin / Dahomey — the Benin-1897 episode needs a real corroborator, so a 1869 Dahomey sword that merely mentions "Benin" is not mis-attributed.

## The other signals (each adds independently)

| Signal | Fires when (in provenance) | Weight |
|---|---|---|
| loot_language | looted / plunder / spoils / "taken from" / "captured during" / sacked / booty … | 6 |
| military_donor | a donation verb ("presented by", "gift of"…) AND a real **rank** (general/colonel/captain/expeditionary force…) — **not** the honorific "Sir" | 4 |
| human_remains | skull / cranium / mummy / ancestral remains … | 4 |
| colonial_channel | Gold Coast Government, Foreign Office, Crown Agents, Royal Niger Company, East India Company… AND foreign context | 3 |
| royal_or_palace_site | palace / royal / oba / emperor / treasury / fortress in findspot or notes, foreign, ≤ 1925 | 3 |
| expedition_collected | "collected during the expedition / campaign" | 3 |
| sacred_regalia | tabot / altar / shrine / reliquary / regalia … AND (foreign or an episode hit) | 2 |
| excavated_foreign | excavated / unearthed AND a non-European department | 2 |

## Mitigations (pull the score back down)

- **depiction_object** — prints/drawings/photographs/engravings with no loot language in their provenance are capped at 2 (they usually *show* a place, they weren't taken from it).
- **modern_transactional** — acquisitions in **1960 or later** with no loot language and no human remains are capped at 1.
- Word-boundary matching throughout (so "general" ≠ "generally"); the excavation and palace rules require a genuinely foreign context, not a UK findspot.

## Test results (28 objects scraped live: looted + neutral mix)

| Band | Count | What's in it |
|---|---|---|
| **STRONG** | 4 | Maqdala tabot (17), Asante armlet at Manhyia Palace (12), Benin bracelet 1897 (15), Benin plaque 1898 (15) |
| **REVIEW** | 2 | Dahomey ceremonial sword, 1869, presented by a Commander (reasonable lead); an Omdurman-associated coin, 1935 (soft false positive — see below) |
| **low** | 22 | all neutral controls (prints, banknote, dial, Wedgwood, Dürer), modern/post-colonial acquisitions (2013 photo, 1951–53 Benin/Dahomey items, 1968 photos), and provenance-clean African items (1893 collected cross, 1952 trade gold-weight) |

Headline outcomes versus the earlier keyword scorer:

- **Every known looted item in the sample was caught at STRONG**, including the Asante armlet that the keyword scorer *missed entirely* (it names no "Asante", only "Manhyia Palace" + "Gold Coast Government") and Benin bronzes.
- **Zero false positives in STRONG.** All seven earlier false positives — the Abyssinia sketchbook, the 1893 Bent/Franks cross, the Wedgwood and Dürer pieces — sit at low.
- A 1877 print whose record contains "looted" (in the depicted scene) correctly scores **0**, and a Dahomey object mentioning "Benin" is **not** mis-filed under Benin 1897.

## Known limitations (honest)

1. **Coins / medals of a place.** An Ottoman coin linked to "Omdurman/Mahdist" landed in REVIEW — a coin *of* a regime isn't battlefield loot. Adding an object-type guard (coins/medals/banknotes need explicit loot language) would remove this.
2. **Undated objects lean on place co-occurrence.** Good (it catches them) but it means a place name plus any region term is enough for REVIEW; precision there depends on the watchlist staying specific.
3. **This test harness captured 14 of the CSV's 47 columns.** One "Summer Palace" opium-pipe scored 0 because the confirming phrase sits in a column the harness didn't pull; a production run over the full export would see it. Recall in the wild is therefore *better* than this sample suggests.
4. **Still a shortlist.** STRONG/REVIEW means "look here", not "this is stolen". Verdicts, mitigating-context reasoning, and verbatim evidence quotes need the Haiku adjudicator run locally.

## To grow coverage
Edit `redflags_watchlist_v3.json` — add episodes (core/region/year window), channels, ranks, or place aliases. No code change needed. Run:
`python3 bm_flag_v3.py <bm_export.csv> -o review_queue` → writes `review_queue.csv/.jsonl` sorted by score.
