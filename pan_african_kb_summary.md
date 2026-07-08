# Pan-African redflag strengthening

Scope is now the whole of Africa, so the KB was rebuilt from a West-Africa-plus-Ethiopia pilot into continent-wide coverage. This is the file Haiku actually uses (`redflags_africa.json`), and the standalone scorer's watchlist (`redflags_watchlist_v4.json`) was mirrored to match.

## Coverage before → after

- **Incidents: 9 → 20.** Added Anglo-Zulu 1879, Matabele/Ndebele 1893-96, Great Zimbabwe soapstone-bird removals, Sokoto Caliphate 1903, Anglo-Aro 1902, Herero & Nama genocide 1904-08, French Madagascar 1895, fall of Segou/Tukulor 1890, Samori/Wassoulou 1898, Gaza/Gungunhana 1895, Bunyoro & East African campaigns, Congo Free State coercive collecting, Bamum/Cameroon, Italian Ethiopia 1936, and Egypt/Nubia (with an excavation caveat).
- **Actors: 17 → 22.** Added Lugard, Rhodes, Kitchener, Baden-Powell, Goldie, Harry Johnston, Archinard, Dodds, Torday, Frobenius — the officers and collectors behind those campaigns.
- **Channels: 6 → 12.** Added the British South Africa Company, Imperial British East Africa Company, African Lakes Company, German colonial administration, Colonial Office, Wellcome.
- **Regions: 3 → 15.** Nigeria, Ethiopia, Ghana, Benin Rep., Sudan, South Africa, Zimbabwe, Congo, Cameroon, Namibia, East Africa, Mali/Sahel, Mozambique/Angola, Madagascar, Egypt — each with culture terms (Zulu, Shona, Kongo, Kuba, Herero, Bamana, Merina…).
- **Object priors added** so an object's identity shortlists it regardless of date: Great Zimbabwe soapstone bird, Kongo nkisi/minkisi/nkondi, Kuba ndop, Ethiopian tabot/cross/crown, Sokoto Arabic manuscript, Herero/Nama ancestral remains — alongside the existing Benin brass/ivory and Asante gold priors.
- **Methods broadened:** added pacification, punitive patrol, "brought back from," district-officer collecting, royal-kraal seizure, war trophy.
- **Mitigations broadened:** added licensed excavation / partage (for Egyptian/Nubian archaeology) and "made for the trade / tourist art," so the shortlister's wide net doesn't push everything to `unfair`.

## Validated

Ran six diverse African objects through the shortlister. Every one now matches the right context (old KB caught none of these):

| Object | Shortlisted as |
|---|---|
| Zulu headrest, Ulundi 1879 | zulu_1879 + south_africa + expedition_participant + palace_until |
| Great Zimbabwe soapstone bird, 1905 | great_zimbabwe + BSA Company + zimbabwe |
| Kongo nkisi nkondi, Torday, 1900 | congo_free_state + actor Torday + congo |
| Sokoto Arabic manuscript, 1903 | sokoto_1903 + nigeria + presented_by_officer |
| Herero skull, 1907 | herero_nama_1904 + german_colonial + namibia + human_remains |
| Modern European bowl | *not shortlisted* (correct) |

## Design note (important for the run)

The shortlister is deliberately a **high-recall net** — it advances anything that names an African region, culture, episode, actor, channel, or a court/ritual object type. That means on a full African run it will hand Haiku a lot of candidates, including ordinary market-made or excavated pieces. That's intended: **Haiku is the precision filter** (and the laundered test showed it distinguishes Owo from Benin, excavation from looting, arm's-length sales from loot). The broadened mitigations exist to keep it from over-calling. So expect a large shortlist and a smaller `unfair` set — and treat every output as a research lead, per the project's own rule.

Files updated: `redflags_africa.json` (the KB Haiku uses) and `redflags_watchlist_v4.json` (the standalone scorer). Both drop straight into the run folder.
