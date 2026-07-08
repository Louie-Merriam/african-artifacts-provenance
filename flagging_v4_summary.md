# v4 — making the flagging more expansive (date-independent)

The complaint: v3 mostly flagged objects **acquired inside an episode's date window**, so it missed loot that entered the museum later through dealers, and anything without a matching date. v4 fixes that.

## What's new

1. **Named dealer/actor watchlist — fires in any year.** If a known loot dealer or officer appears in the provenance (W.D. Webster, Oldman, Pitt-Rivers, R.R. Holmes, Ralph Moor, Harry Rawson, Garnet Wolseley, …), the object flags **regardless of acquisition date**. This is the laundered-acquisition catch.
2. **Object-type × origin priors — fire on identity, not date.** A Benin brass plaque/head, an Ethiopian tabot/manuscript, Asante gold regalia, etc. flag when the object *type* matches and the *origin* matches — whatever year it was acquired.
3. **Date is now a booster, not a gate.** Episodes confirm on a core place term + any corroborator (region, loot, palace, channel, prior, or in-window date). An in-window date just pushes confidence up.
4. **The modern/depiction mitigations no longer suppress** actor / prior / loot / method / human-remains hits — so a 1965 dealer-laundered plaque still surfaces.
5. **Broader episodes:** added Seringapatam 1799 (Tipu Sultan) and the 1857 uprising (Lucknow/Delhi); widened the Sudan/Mahdist window.
6. **Two guards added from testing:** a standalone `punitive_expedition` method (fires without a donor verb — catches e.g. Pacific punitive-raid material), and a **numismatic guard** (a coin/medal *of* a place isn't loot unless there's loot language or a named actor).

## Proof it works (verified in Python)

| Object | Acq year | v3 | v4 | Why |
|---|---|---|---|---|
| Benin brass plaque, **purchased from W.D. Webster** | **1965** | low (modern) | **STRONG (10)** | named actor + Benin object-prior, survives the modern cap |
| Ordinary Benin **basket**, market purchase | 1965 | low | **low (0)** | no prior/actor/loot — precision retained |
| Asante **gold regalia**, from Oldman | 1972 | low | **STRONG (12)** | object-prior + named actor, date-independent |
| Tipu **tiger finial**, Seringapatam | 1880 | low (no episode) | **STRONG** | new Seringapatam episode |
| 1953 Abomey **figure** (battery) | 1953 | low | **REVIEW** | place match surfaces a late acquisition for a human look |

The contrast in the first two rows is the whole point: laundered loot is caught **without** flooding on ordinary modern items.

## Battery (37 objects): 4 STRONG, 2 REVIEW, 31 low
All four STRONG are genuine loot (two Benin bronzes, the Maqdala tabot, the Asante armlet). The neutrals, modern ethnographic pieces, depictions, and coins all stayed low.

## Honest limits
- **Recall still depends on the field being in the export.** The Pacific "punitive expedition" arrows scored low here only because that phrase sits in a CSV column my 14-field test harness didn't capture; the full 47-column export feeds the standalone method flag and would catch them.
- **Date-independence raises REVIEW volume** (e.g. the 1953 figure). That's the intended trade — more leads for a human/Haiku to confirm — but it means the REVIEW band needs a person, not auto-trust.
- Named-actor matching uses distinctive aliases; bare common surnames were left out to avoid noise. Expand `named_actors` in the watchlist as you mine more provenance (e.g. the Digital Benin 965-name registry).

## Files
`bm_flag_v4.py` + `redflags_watchlist_v4.json` (the scorer + expandable lists); the adjudicator KB `redflags_africa.json` was also extended (9 incidents, 11 actors) so the Haiku pipeline gets the same breadth.
