# Validation cases — the method reasoning through hard cases

*Nine real records from the full run (`out/full_adjudicated.jsonl`), selected so that each demonstrates a distinct capability the method claims. Verdicts, evidence quotes, and rationales are the model's verbatim output (rationales trimmed with …). Together they show the two-tier design working as intended: flags trigger review; the model then discriminates case-by-case — condemning, clearing, hedging, or being overruled by its own guardrails.*

---

## 1. The laundering case — dealer chain, no seizure language needed
**Af1911,0620.1 — bronze aquamanile, Benin City. Purchased from W.O. Oldman, 1911. → unfair (high)**
Flags: incident `benin_1897`, actor `oldman`. Quotes: *"British Expedition to Benin City, 1897. Purchased from the dealer W O Oldman in 1911"; "Made in: Benin City."*
> "This aquamanile was made in Benin City and acquired in 1911 from William Ockelford Oldman, a watch-listed dealer known to handle colonial-era loot including Benin material. The acquisition notes explicitly reference the British Expedition to Benin City in 1897, which sacked the city and seized thousands of brass plaques and court objects…"

*Demonstrates:* a purchase fourteen years after the sack, through the market, is not cleaned by the sale — the dealer flag plus object-origin prior carries the verdict.

## 2. The very late arrival — loot accessioned 66 years after seizure
**Af1963,04.1 — ivory double-gong, Benin City, acquired 1963. → unfair (high)**
Flags: incident `benin_1897`, Digital Benin registry actor, method `presented_by_officer`. Quotes: *"Formerly in the collection of Admiral Egerton, who collected it on the Benin Expedition of…"*
> "…explicitly documented as collected by Admiral Egerton during the 1897 Benin Punitive Expedition… The acquisition chain (officer → donation) matches the classic laundering pattern. No mitigating features (legitimate pre-1897 acquisition, documented consent, or independent provenance) are present."

*Demonstrates:* date-independence. A 1963 accession would pass any date-gated detector; the officer-collection line in the provenance still convicts it.

## 3. Context inference — no loot word anywhere in the record
**Af1896,0512.82 — gold armlet. "Found/Acquired: Manhyia Palace | Donated by: Gold Coast Government | 1896." → unfair (high)**
Flags: incident `asante_wars`, channel `gold_coast_government`. Quotes: *"Found/Acquired: Manhyia Palace"; "Donated by: Gold Coast Government."*
> "The armlet was acquired from Manhyia Palace in 1896 via donation from the Gold Coast Government, precisely during the British occupation of Kumasi and exile of Asantehene Prempeh… The object is a gold regalia item from the Asante palace, seized during military occupation. No mitigating features document legitimate pre-looting acquisition or consensual transfer…"

*Demonstrates:* the model supplies the historical fact the record omits (1896 = occupation of Kumasi, exile of Prempeh I) and reasons from findspot + donor + date. This is the exact record used as the hand-worked example in the paper's introduction — the machine reproduces the human deduction.

## 4. The direct-evidence baseline — and sacred-object calibration
**Af1868,1005.4 — tabot, Maqdala. Donated by the Secretary of State for India's circle, 1868. → unfair (high)**
Flags: incident `maqdala_1868`, methods `spoils_language`, `palace_until`. Quotes: *"Part of a collection of material taken from the fortress of Emperor Tewodros II…"; "The Tabot is the foundation of the Ethiopian Orthodox church…"*
> "This tabot was seized during the 1868 British military assault on Emperor Tewodros II's fortress at Maqdala. The record explicitly states it was 'taken from the fortress'… A tabot is a sacred liturgical object central to Ethiopian Orthodox Christianity — a court/ritual object of profound cultural and religious significance…"

*Demonstrates:* the easy case handled cleanly, with the object's ritual status explicitly weighed per the calibration rule (court/ritual object ⇒ strong).

## 5. Temporal exoneration — flagged dealer, cleared object
**1853,0212.73.4-5 — print/book illustration, purchased from Bernard Quaritch, 1853. → insufficient_evidence (low)**
Flags: actor `quaritch`. Quote: *"Purchased from: Bernard Quaritch."*
> "While Bernard Quaritch is flagged as a dealer who handled Ethiopian manuscripts traceable to the 1868 Maqdala dispersal, this object is a print/book-illustration purchased in 1853 — **before** the Maqdala incident. The record does not identify this object as Ethiopian or as part of any looted collection… Without evidence linking this particular object to a looting inc[ident]…"

*Demonstrates:* the escape hatch working. The registry flags every Quaritch purchase; the model checks the date, notes the acquisition predates the event the dealer is flagged for, and declines to condemn. Flag ≠ verdict, by construction.

## 6. Mitigation wins — diplomacy before empire
**Af1818,1114.26 — bag, Asante. Donated by Thomas Edward Bowdich, 1818. → fair (high)**
Flags: incident `asante_wars`, method `expedition_participant`. Quotes: *"Donated by: Thomas Edward Bowdich"; "collection made by Thomas Edward Bowdich while a member of the British embassy to the Asan[te court]"…*
> "Bowdich acquired this bag in 1817 as a member of a diplomatic embassy to the Asante court, predating the Anglo-Asante Wars (1874–1901) by decades… The acquisition was consensual and occurred during a peaceful diplomatic mission, not during any conflict or sack of Kumasi."

*Demonstrates:* the same court that dominates the unfair column (Manhyia Palace, 92% unfair) is judged **fair** when the record documents 1817 diplomatic exchange — the system discriminates circumstances, not peoples.

## 7. The guardrail overrules the model — integrity over recall
**Af1897,1224.3 — altar-tusk, Benin City, donated by Sir William Ingram, 1897. → insufficient_evidence (downgraded)**
Flags: incident `benin_1897`, method `spoils_language`. Surviving quotes: none.
> "[downgraded: fabricated/unverifiable quotes removed] The object record explicitly states the altar-tusk was 'looted by British soldiers from the royal palace'… "

*Demonstrates:* the deterministic quote validator found the model's "quotes" were not verbatim substrings of the record, stripped them, and auto-downgraded an unfair verdict that could not display its evidence — even though the object is, in all likelihood, genuine 1897 loot. 164 records ended in this state. The system deliberately prefers losing a probable true positive to asserting one on unverifiable evidence; these 164 are flagged for exactly the human re-review the pipeline is designed to feed.

## 8. Flag rejected — the watch-listed name is incidental
**Af1951,12.274.a — object from the Fagg fieldwork collection, DRC, purchased 1951. → transactional (medium)**
Flags: actor `torday` (mentioned in curators' comments). Quotes: *"Field Collection by: William Fagg"; "Purchased from: William Fagg."*
> "…Although the record mentions Torday's ethnographic work and the object is from the DRC, the acquisition was through direct fieldwork by Fagg in the late 1940s and a documented purchase from him in 1951 — a clean, arm's-length transaction dated decades after the high-risk colonial violence window…"

*Demonstrates:* a shortlist hit (Torday's name appearing in a comparative curatorial note) correctly rejected. The shortlister is built over-inclusive; the adjudicator exists to disagree with it, and does.

## 9. Documentation, not loot — the depiction distinction
**Af,A157.70 — photographic prints from Charles Partridge's 1911–12 tour. → insufficient_evidence (low)**
Flags: actor `axr_a_charles_partridge`, method `spoils_language`.
> "Charles Partridge is flagged as a District Commissioner… whose collections merit review due to formation under military-occupation conditions. However, the object record describes photographic prints taken during Partridge's 7th tour… during boundary delimitation between Nigeria and Dahomey — activities consistent with administrative documentation rather than looting…"

*Demonstrates:* restraint on the largest false-positive class. A flagged colonial officer's photographs are treated as documentation of the colonial context, not condemned as loot; the model withholds judgment absent seizure evidence.

---

## Summary table for the paper

| # | reg | challenge | verdict | capability shown |
|---|---|---|---|---|
| 1 | Af1911,0620.1 | dealer purchase, 14 yrs post-loot | unfair (high) | laundering rule |
| 2 | Af1963,04.1 | accessioned 66 yrs post-loot | unfair (high) | date-independence |
| 3 | Af1896,0512.82 | no loot word in record | unfair (high) | historical context inference |
| 4 | Af1868,1005.4 | explicit seizure record | unfair (high) | baseline + sacred-object calibration |
| 5 | 1853,0212.73.4-5 | flagged dealer, pre-event purchase | insufficient (low) | temporal exoneration / escape hatch |
| 6 | Af1818,1114.26 | flagged episode region, 1817 gift | fair (high) | mitigation; circumstances not peoples |
| 7 | Af1897,1224.3 | model paraphrased its evidence | insufficient (downgraded) | guardrail overrules model |
| 8 | Af1951,12.274.a | watch-listed name incidental | transactional (medium) | flag rejection |
| 9 | Af,A157.70 | flagged officer's photographs | insufficient (low) | depiction/documentation restraint |
