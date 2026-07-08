# Real Haiku vs v4 rules vs mock — 6-object sample

First real Haiku run (`claude-haiku-4-5-20251001`). 5 of 6 shortlisted; the 2013 Tiya photo never matched the KB so never hit the model.

| Object | Haiku | conf | v4 rules | mock |
|---|---|---|---|---|
| Af1868,1005.4 — tabot, "taken from the fortress at Maqdala" | **unfair** | high | STRONG (17) | transactional |
| Af1896,0512.82 — armlet, Manhyia Palace, Gold Coast Govt, 1896 | **unfair** | high | STRONG (12) | transactional |
| 1895,0408.6.8 — Zander drawing of Abyssinia, purchased 1895 | transactional | medium | low (0) | transactional |
| Af1952,13.12 — gold-weight, U.A.C. agent, Ghana | insufficient_evidence | low | low (0) | transactional |
| Af1893,1111.170 — cross, collected by Bent 1893, Franks gift | insufficient_evidence | low | low (0) | transactional |

## What this tells us

**Haiku and the v4 rules agree on all five.** Both call the two loots unfair/STRONG and leave the three non-loots alone. The rules and the model converge — good cross-validation of both.

**The mock is useless for verdicts** — it labeled all five "transactional," including the blatant Maqdala tabot. Confirmed: the deterministic stub only tests plumbing.

**The Manhyia armlet is the answer to "how much is Haiku reasoning?"** That record contains **no loot word at all** — just findspot "Manhyia Palace," donor "Gold Coast Government," date 1896. Haiku returned **unfair, high confidence**, with this rationale:

> "acquired in 1896 from Manhyia Palace (the Asante royal residence in Kumasi) … precisely matching the date and circumstances of the British military occupation and sacking of Kumasi in 1896, when palace contents and gold regalia were seized."

That is genuine independent reasoning: Haiku supplied the historical fact (1896 = sack of Kumasi) that the record omits, and inferred looting from palace + colonial-government-donor + year. This is the same conclusion v4 reaches through its palace/channel priors — but Haiku got there by *knowing the history*, and cited the findspot/donor as evidence instead of a loot quote. So on cases with strong contextual signals, Haiku does real inference, not just keyword-echoing.

**Haiku's discrimination on the soft cases is good:** it correctly read the Zander drawing as an arm's-length 1895 purchase (transactional), and hedged the U.A.C. gold-weight and the Bent/Franks cross to insufficient_evidence — reasoning that a legitimate trading company and an 1893 collection date, absent a flagged actor, don't establish looting. That restraint is exactly the "don't over-flag everything African" goal.

## Two issues found

1. **Malformed evidence quote (bug).** For the Zander drawing, `evidence_quotes` came back as a list of single characters ("P | u | r | c | h | …") and the text was a slightly fabricated paraphrase ("acuisition date"), not an exact substring. `validate_quotes` didn't catch it because single characters trivially pass the substring test. Cheap fix: drop quote fragments shorter than ~4 chars (or require the whole quote to be an exact substring, not just its first 60 chars).

2. **The real test is still ahead.** This sample had explicit signals (loot language, or palace+government+year). The **laundered 12** — Benin court objects via Oldman/Webster/Glendining with *no* palace, channel, or loot cue — are the harder case. Given Haiku inferred history for the Manhyia armlet, the open question is whether it will also infer "Benin court object + known loot-dealer chain ⇒ 1897 loot," or hedge to insufficient_evidence without a contextual hook. That run decides whether the dealer-chain reasoning lives in the model or only in the v4 rules.
