# Laundered-case test — real Haiku (12 Benin objects, no loot keyword)

Run on the **improved KB** (dealers + Benin object-priors wired into `redflags_africa.json`). The `matched_flags` confirm Haiku used the new entries (`oldman`, `db_burney`, `db_glendining`, `db_fenton`, `db_plass`, `benin_1897` with object-priors).

Verdicts: **7 unfair, 3 transactional, 1 insufficient_evidence, 1 never shortlisted.**

| Reg | Object | Via | Haiku | The reasoning |
|---|---|---|---|---|
| Af1979,01.4560 | altar-tusk | Oldman (1949) | **unfair** | *inference:* court object + flagged dealer + Benin City → loot profile. No expedition text in record. |
| Af1922,0714.1 | ivory arm-cuff | Glendining (1922) | **unfair** | Benin City ivory via a laundering auction node in the post-1897 dispersal window. |
| Af1911,0620.1 | aquamanile | Oldman (1911) | unfair | found "British Expedition to Benin City, 1897" in the notes. |
| Af1928,0112.2 | anklet | Burney | unfair | found "collected by Ralph Locke, survivor of the Benin massacre." |
| Af1963,04.1 | gong | Plass | unfair | traced to "Admiral Egerton, collected on the Benin Expedition of 1897." |
| Af1902,0516.25 | hair-pin | Fenton | unfair | note: "may imply it came from the British Benin Expedition, 1897" + flagged dealer. |
| Af1954,23.1489 | anklet | Wellcome/Stevens | unfair | "massive Benin bronze anklet," Stevens' 1918 sale (dispersal chain). |
| Af1949,46.161 | altar | Oldman (1949) | **transactional** | Oldman + Benin City — *but* judged the 1949 sale from Oldman's widow a documented arm's-length modern sale, 52 years on. Mitigation outweighed. |
| Af1930,0423.9 | armlet | F.W. Burt | **transactional** | *rejected the flag:* "production place is Owo, not Benin"; found by a local at Apapa in 1907. Not Benin loot. |
| Af1909,0811.9 | armlet | Lady Macdonald | **transactional** | *rejected the flag:* "discovered in the earth" at Forcados River — archaeological excavation, not palace looting. |
| Af1979,01.4561 | altar-tusk | Oldman (?) | insufficient_evidence | near-identical to the unfair altar-tusk, but "Details of acquisition uncertain" → hedged. |
| Af1979,01.4450 | armlet | — | (not shortlisted) | no donor/findspot text matched the KB; never reached the model. |

## What this actually shows

**1. Haiku does carry the laundering inference.** The altar-tusk Af1979,01.4560 has *no* expedition language — just "altar-tusk, Benin City, from Oldman." Haiku called it unfair (high) by reasoning that a Benin court object from a flagged dealer fits the 1897 loot profile. That's the hardest inference in the project, and it did it. The `why_flag` context we wired into the KB is what let it.

**2. The bigger surprise: Haiku out-discriminates the rules on false positives.** This is where it beats `bm_flag_v4`, which would have flagged all 12 (dealer + Benin region/prior):
- **Af1930** — Haiku saw the object is from **Owo, not Benin City** (a different Nigerian kingdom) and downgraded to transactional. The rules can't tell Owo from Benin.
- **Af1909** — Haiku saw it was **excavated from a riverbed**, not taken from the palace, and downgraded. The rules treat "Benin + old" as loot.
- **Af1949** — Haiku applied the **arm's-length modern sale** mitigation (Oldman's widow, 1949) and declined to call it unfair.
- **Af1979,01.4561** — hedged to insufficient_evidence on **explicitly uncertain** provenance, while calling its near-twin unfair.

That is genuine, case-by-case judgment the deterministic layer cannot reproduce.

## Honest caveat on the test

My "no loot word" filter was leaky: it screened for loot/spoils/plunder/etc. but **not** "British Expedition," "Benin massacre," or "1897," so several of the 7 unfair calls (Af1911, Af1928, Af1963, Af1902) were actually **evidence-based** — Haiku found and quoted explicit expedition provenance buried in the curators' comments. Those are wins for reading free-text, not pure inference. The genuinely laundered cases (dealer-only, no expedition text) were fewer — the altar-tusks and the arm-cuff — and Haiku split them intelligently (inference → unfair; uncertainty → insufficient).

## Net answer to "how much independent reasoning is Haiku doing?"

On easy cases (explicit loot text): little — a regex matches too. On this harder set: **a lot, and it's the reasoning the rules can't do** — distinguishing Owo from Benin, excavation from looting, an arm's-length modern sale from a laundering chain, and certain from uncertain provenance. The division of labor that emerges: **the rules cast a wide, cheap net (flag every Benin-court-object-via-dealer); Haiku is the precision filter that decides which are actually loot and why, with citations.** That's a genuinely strong pairing — and the opposite of the worry that Haiku was just echoing keywords.
