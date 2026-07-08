#!/usr/bin/env python3
"""
bm_provenance_extractor.py
==========================
Extract, normalize, and red-flag the provenance / acquisition history of
British Museum objects.

The hard part of "scraping the British Museum" is that there is no single clean
public object API:

  * The new collection site (britishmuseum.org/collection/object/{id}) is a
    client-rendered JS app — a plain HTTP GET returns an empty shell.
  * The CIDOC-CRM SPARQL endpoint (collection.britishmuseum.org) is the only
    structured, automatable endpoint, but it is frequently slow or down.
  * The website's *CSV export* of any search result is reliable and contains
    the full acquisition schema (Find spot, Acq name, Acq date, Acq notes...).

So this tool is source-agnostic. It has three input adapters that all feed the
same normalization + red-flag pipeline:

  1. csv     -- parse one or more CSV files exported from BM Collection Online
                search results.  RELIABLE. Recommended default.
  2. sparql  -- harvest acquisition data directly from the BM SPARQL endpoint
                with retry/backoff + resumable checkpointing.  Automatable but
                depends on the endpoint being up.
  3. json    -- parse per-object JSON saved from the site's internal API
                (endpoint configurable; see --api-url).  For when you have
                captured the live endpoint via browser devtools.

Output: a normalized CSV and a JSONL file where every record carries
`flags` (list of triggered red-flag rules) and a `flag_score`.

Usage
-----
  # Recommended: export CSVs from the BM site, then:
  python bm_provenance_extractor.py csv exports/*.csv -o out/benin

  # Direct SPARQL harvest of a culture/region (endpoint permitting):
  python bm_provenance_extractor.py sparql --culture "Benin" --limit 500 -o out/benin

  # Test whether the SPARQL endpoint is alive right now:
  python bm_provenance_extractor.py sparql --test

Red-flag rules live in redflag_rules.json (edit freely — this is where you
encode YOUR theory of "unfair seizure").
"""

from __future__ import annotations

import argparse
import csv as csvmod
import dataclasses
import glob
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional

csvmod.field_size_limit(10_000_000)

LOG = logging.getLogger("bm")

SPARQL_ENDPOINT = "https://collection.britishmuseum.org/sparql"
USER_AGENT = "bm-provenance-research/1.0 (academic provenance study; contact: you@example.org)"

# ---------------------------------------------------------------------------
# Unified record schema
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceRecord:
    """One British Museum object, normalized across all input sources."""
    object_id: str = ""              # museum number / registration number / URI tail
    title: str = ""
    object_type: str = ""
    culture: str = ""                # "Culture" / "Ethnic name"
    production_place: str = ""
    findspot: str = ""               # where it was physically found / removed from
    acquisition_from: str = ""       # donor / seller / "Acq name (acq)"
    acquisition_finder: str = ""     # "Acq name (finding)"
    acquisition_excavator: str = ""  # "Acq name (excavator)"
    acquisition_previous: str = ""   # "Acq name (previous)"
    acquisition_date: str = ""       # raw "Acq date"
    acquisition_year: Optional[int] = None   # parsed 4-digit year, best-effort
    acquisition_notes: str = ""      # "Acq notes (acq)" + "(exc)"
    provenance_text: str = ""        # any free-text ownership history
    department: str = ""
    source: str = ""                 # csv | sparql | json
    source_url: str = ""
    flags: List[str] = field(default_factory=list)
    flag_score: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)

    # The big haystack the rule engine searches over.
    def searchable_text(self) -> str:
        parts = [
            self.title, self.object_type, self.culture, self.production_place,
            self.findspot, self.acquisition_from, self.acquisition_finder,
            self.acquisition_excavator, self.acquisition_previous,
            self.acquisition_notes, self.provenance_text,
        ]
        return " ‖ ".join(p for p in parts if p).strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20[0-2]\d)\b")

def parse_year(text: str) -> Optional[int]:
    """Best-effort: pull the first plausible acquisition year from a string."""
    if not text:
        return None
    m = _YEAR_RE.search(text)
    return int(m.group(1)) if m else None


def _first(d: Dict[str, str], *keys: str) -> str:
    """Return the first non-empty value among a set of candidate column names
    (case/spacing-insensitive)."""
    norm = {re.sub(r"[^a-z0-9]", "", k.lower()): v for k, v in d.items()}
    for k in keys:
        nk = re.sub(r"[^a-z0-9]", "", k.lower())
        if norm.get(nk):
            return norm[nk].strip()
    return ""


# ---------------------------------------------------------------------------
# Input adapter 1: CSV export from BM Collection Online (RELIABLE)
# ---------------------------------------------------------------------------

def from_csv(paths: List[str]) -> Iterable[ProvenanceRecord]:
    files: List[str] = []
    for p in paths:
        files.extend(sorted(glob.glob(p)))
    if not files:
        LOG.error("No CSV files matched: %s", paths)
        return
    for path in files:
        LOG.info("Reading %s", path)
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csvmod.DictReader(fh)
            for row in reader:
                yield _record_from_csv_row(row, path)


def _record_from_csv_row(row: Dict[str, str], path: str) -> ProvenanceRecord:
    acq_notes = " ".join(filter(None, [
        _first(row, "Acq notes (acq)", "Acq notes acq", "Acquisition notes"),
        _first(row, "Acq notes (exc)", "Acq notes exc"),
    ]))
    obj_id = _first(row, "Museum number", "BM/Big number", "Reg number",
                    "Registration number", "Object number")
    rec = ProvenanceRecord(
        object_id=obj_id,
        title=_first(row, "Title", "Object type"),
        object_type=_first(row, "Object type", "Object name"),
        culture=_first(row, "Culture", "Ethnic name (made by)", "Ethnic name"),
        production_place=_first(row, "Production place", "Production places"),
        findspot=_first(row, "Find spot", "Findspot"),
        acquisition_from=_first(row, "Acq name (acq)", "Acq name acq", "Acquisition name"),
        acquisition_finder=_first(row, "Acq name (finding)", "Acq name finding"),
        acquisition_excavator=_first(row, "Acq name (excavator)", "Acq name excavator"),
        acquisition_previous=_first(row, "Acq name (previous)", "Acq name previous"),
        acquisition_date=_first(row, "Acq date", "Acquisition date"),
        acquisition_notes=acq_notes,
        provenance_text=_first(row, "Provenance", "Curators comments", "Comments", "Curator's comments"),
        department=_first(row, "Dept", "Department"),
        source="csv",
        source_url=(f"https://www.britishmuseum.org/collection/object/{obj_id}"
                    if obj_id else ""),
        raw=row,
    )
    rec.acquisition_year = parse_year(rec.acquisition_date) or parse_year(rec.acquisition_notes)
    return rec


# ---------------------------------------------------------------------------
# Input adapter 2: SPARQL harvest (automatable, endpoint permitting)
# ---------------------------------------------------------------------------

# British Museum CIDOC-CRM (Erlangen namespace) + ResearchSpace ontology.
# NOTE: BM's model is deep; treat this template as a starting point and adjust
# predicates against the live endpoint (run with --test first). The CSV path
# does NOT depend on this query being perfect.
SPARQL_TEMPLATE = """
PREFIX ecrm: <http://erlangen-crm.org/current/>
PREFIX bmo:  <http://www.researchspace.org/ontology/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?object ?museumNumber ?objectType ?title
       ?prodPlace ?findspot ?acqFrom ?acqDate ?acqNote
WHERE {{
  ?object a ecrm:E22_Man-Made_Object .
  OPTIONAL {{ ?object bmo:PX_object_type/skos:prefLabel ?objectType . }}
  OPTIONAL {{ ?object rdfs:label ?title . }}
  OPTIONAL {{ ?object ecrm:P1_is_identified_by ?id . ?id a bmo:PX_Object_Number ; rdfs:label ?museumNumber . }}
  OPTIONAL {{ ?object ecrm:P12i_was_present_at/ecrm:P7_took_place_at/skos:prefLabel ?findspot . }}
  OPTIONAL {{ ?object bmo:PX_production_place/skos:prefLabel ?prodPlace . }}
  OPTIONAL {{
    ?acq a ecrm:E8_Acquisition ; ecrm:P24_transferred_title_of ?object .
    OPTIONAL {{ ?acq ecrm:P23_transferred_title_from/rdfs:label ?acqFrom . }}
    OPTIONAL {{ ?acq ecrm:P4_has_time-span/rdfs:label ?acqDate . }}
    OPTIONAL {{ ?acq ecrm:P3_has_note ?acqNote . }}
  }}
  {filter_block}
}}
LIMIT {limit} OFFSET {offset}
"""

def _sparql_get(query: str, timeout: int = 60) -> Dict[str, Any]:
    url = SPARQL_ENDPOINT + ".json?" + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sparql_test() -> bool:
    LOG.info("Testing SPARQL endpoint %s ...", SPARQL_ENDPOINT)
    try:
        data = _sparql_get("SELECT * WHERE { ?s ?p ?o } LIMIT 1", timeout=30)
        n = len(data.get("results", {}).get("bindings", []))
        LOG.info("Endpoint responded (%d row). It is UP.", n)
        return True
    except Exception as e:  # noqa: BLE001
        LOG.error("Endpoint did not respond: %s", e)
        return False


def from_sparql(culture: str = "", limit: int = 500, page_size: int = 100,
                checkpoint: str = "", max_retries: int = 5) -> Iterable[ProvenanceRecord]:
    filter_block = ""
    if culture:
        # crude but effective: filter on any label containing the term
        safe = culture.replace('"', '\\"')
        filter_block = f'FILTER(CONTAINS(LCASE(STR(?title)), "{safe.lower()}") ' \
                       f'|| CONTAINS(LCASE(STR(?prodPlace)), "{safe.lower()}"))'

    offset = 0
    if checkpoint and os.path.exists(checkpoint):
        offset = int(open(checkpoint).read().strip() or "0")
        LOG.info("Resuming from offset %d (checkpoint %s)", offset, checkpoint)

    fetched = 0
    while fetched < limit:
        this_page = min(page_size, limit - fetched)
        q = SPARQL_TEMPLATE.format(filter_block=filter_block, limit=this_page, offset=offset)
        data = _retry(lambda: _sparql_get(q), max_retries)
        if data is None:
            LOG.error("Giving up at offset %d after retries.", offset)
            break
        rows = data.get("results", {}).get("bindings", [])
        if not rows:
            LOG.info("No more rows at offset %d. Done.", offset)
            break
        for b in rows:
            yield _record_from_sparql(b)
        n = len(rows)
        offset += n
        fetched += n
        if checkpoint:
            open(checkpoint, "w").write(str(offset))
        LOG.info("Harvested %d / %d", fetched, limit)
        time.sleep(1.0)  # be polite
        if n < this_page:
            break


def _record_from_sparql(b: Dict[str, Any]) -> ProvenanceRecord:
    def v(key: str) -> str:
        return (b.get(key) or {}).get("value", "").strip()
    uri = v("object")
    rec = ProvenanceRecord(
        object_id=v("museumNumber") or uri.rsplit("/", 1)[-1],
        title=v("title"),
        object_type=v("objectType"),
        production_place=v("prodPlace"),
        findspot=v("findspot"),
        acquisition_from=v("acqFrom"),
        acquisition_date=v("acqDate"),
        acquisition_notes=v("acqNote"),
        source="sparql",
        source_url=uri,
        raw={k: v(k) for k in b},
    )
    rec.acquisition_year = parse_year(rec.acquisition_date) or parse_year(rec.acquisition_notes)
    return rec


def _retry(fn, max_retries: int):
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            LOG.warning("Attempt %d/%d failed: %s", attempt, max_retries, e)
            if attempt == max_retries:
                return None
            time.sleep(delay)
            delay *= 2
    return None


# ---------------------------------------------------------------------------
# Input adapter 3: per-object JSON saved from the site's internal API
# ---------------------------------------------------------------------------

def from_json(paths: List[str], mapping: Optional[Dict[str, str]] = None) -> Iterable[ProvenanceRecord]:
    """Parse JSON files/dirs captured from the site's internal API. Because the
    exact shape depends on the (undocumented) endpoint, fields are pulled with a
    configurable dotted-path mapping; defaults are best guesses."""
    mapping = mapping or {
        "object_id": "registrationNumber",
        "title": "title",
        "object_type": "objectType",
        "production_place": "producedAt",
        "findspot": "findspot",
        "acquisition_from": "acquisition.from",
        "acquisition_date": "acquisition.date",
        "acquisition_notes": "acquisition.notes",
        "provenance_text": "provenance",
    }
    files: List[str] = []
    for p in paths:
        files.extend(sorted(glob.glob(p)))
    for path in files:
        try:
            obj = json.load(open(path, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            LOG.warning("Skipping %s: %s", path, e)
            continue
        objects = obj if isinstance(obj, list) else [obj]
        for o in objects:
            rec = ProvenanceRecord(source="json", raw=o if isinstance(o, dict) else {})
            for fieldname, dotted in mapping.items():
                setattr(rec, fieldname, _dig(o, dotted))
            rec.acquisition_year = parse_year(rec.acquisition_date) or parse_year(rec.acquisition_notes)
            yield rec


def _dig(obj: Any, dotted: str) -> str:
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return ""
    if cur is None:
        return ""
    return str(cur).strip()


# ---------------------------------------------------------------------------
# Red-flag engine
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    id: str
    description: str
    weight: int = 1
    any_keywords: List[str] = field(default_factory=list)   # regex, OR
    all_keywords: List[str] = field(default_factory=list)   # regex, AND
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    fields: Optional[List[str]] = None  # restrict search to these record fields

    def matches(self, rec: ProvenanceRecord) -> bool:
        # year window
        if self.year_min is not None or self.year_max is not None:
            y = rec.acquisition_year
            if y is None:
                return False
            if self.year_min is not None and y < self.year_min:
                return False
            if self.year_max is not None and y > self.year_max:
                return False
            if not self.any_keywords and not self.all_keywords:
                return True
        hay = self._haystack(rec)
        if self.all_keywords and not all(re.search(k, hay, re.I) for k in self.all_keywords):
            return False
        if self.any_keywords and not any(re.search(k, hay, re.I) for k in self.any_keywords):
            return False
        return bool(self.any_keywords or self.all_keywords or
                    self.year_min is not None or self.year_max is not None)

    def _haystack(self, rec: ProvenanceRecord) -> str:
        if not self.fields:
            return rec.searchable_text()
        return " ‖ ".join(str(getattr(rec, f, "") or "") for f in self.fields)


def load_rules(path: str) -> List[Rule]:
    data = json.load(open(path, encoding="utf-8"))
    rules = []
    for r in data.get("rules", []):
        rules.append(Rule(**r))
    LOG.info("Loaded %d red-flag rules from %s", len(rules), path)
    return rules


def apply_rules(rec: ProvenanceRecord, rules: List[Rule]) -> None:
    score = 0
    hits: List[str] = []
    for rule in rules:
        try:
            if rule.matches(rec):
                hits.append(rule.id)
                score += rule.weight
        except re.error as e:
            LOG.warning("Bad regex in rule %s: %s", rule.id, e)
    rec.flags = hits
    rec.flag_score = score


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "object_id", "title", "object_type", "culture", "production_place",
    "findspot", "acquisition_from", "acquisition_finder", "acquisition_excavator",
    "acquisition_previous", "acquisition_date", "acquisition_year",
    "acquisition_notes", "provenance_text", "department", "flag_score", "flags",
    "source", "source_url",
]

def write_outputs(records: List[ProvenanceRecord], out_prefix: str,
                  flagged_only: bool = False) -> None:
    os.makedirs(os.path.dirname(out_prefix) or ".", exist_ok=True)
    rows = [r for r in records if (r.flag_score > 0 or not flagged_only)]

    csv_path = out_prefix + ".csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csvmod.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            d = asdict(r)
            d["flags"] = "; ".join(r.flags)
            w.writerow(d)

    jsonl_path = out_prefix + ".jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    flagged = sum(1 for r in records if r.flag_score > 0)
    LOG.info("Wrote %d records (%d flagged) -> %s , %s",
             len(rows), flagged, csv_path, jsonl_path)
    # quick top-flags summary
    from collections import Counter
    c = Counter(f for r in records for f in r.flags)
    if c:
        LOG.info("Top red flags: %s", ", ".join(f"{k}={v}" for k, v in c.most_common(10)))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    # Shared options live on a parent parser so they work both before AND after
    # the subcommand (e.g. `... csv file.csv -o out/x`).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-o", "--out", default="out/bm_provenance",
                        help="output path prefix (writes .csv and .jsonl)")
    common.add_argument("--rules",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "redflag_rules.json"),
                        help="path to red-flag rules JSON")
    common.add_argument("--flagged-only", action="store_true",
                        help="only write records that triggered >=1 red flag")
    common.add_argument("-v", "--verbose", action="store_true")

    p = argparse.ArgumentParser(description=__doc__, parents=[common],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("csv", parents=[common],
                        help="parse CSV exports from BM Collection Online")
    pc.add_argument("paths", nargs="+", help="CSV file(s) or globs")

    ps = sub.add_parser("sparql", parents=[common],
                        help="harvest from the BM SPARQL endpoint")
    ps.add_argument("--test", action="store_true", help="just check if endpoint is up")
    ps.add_argument("--culture", default="", help="filter term (culture/place/title)")
    ps.add_argument("--limit", type=int, default=500)
    ps.add_argument("--page-size", type=int, default=100)
    ps.add_argument("--checkpoint", default="", help="file to store resume offset")

    pj = sub.add_parser("json", parents=[common],
                        help="parse per-object JSON from the site API")
    pj.add_argument("paths", nargs="+", help="JSON file(s) or globs")
    pj.add_argument("--mapping", default="", help="JSON file: field -> dotted path")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s")

    if args.cmd == "sparql" and args.test:
        return 0 if sparql_test() else 2

    rules = load_rules(args.rules)

    if args.cmd == "csv":
        stream = from_csv(args.paths)
    elif args.cmd == "sparql":
        stream = from_sparql(culture=args.culture, limit=args.limit,
                             page_size=args.page_size, checkpoint=args.checkpoint)
    elif args.cmd == "json":
        mapping = json.load(open(args.mapping)) if args.mapping else None
        stream = from_json(args.paths, mapping)
    else:
        LOG.error("Unknown command")
        return 2

    records: List[ProvenanceRecord] = []
    for rec in stream:
        apply_rules(rec, rules)
        records.append(rec)

    if not records:
        LOG.warning("No records produced. (If using sparql, the endpoint may be down — "
                    "try `--test`, or use the csv adapter instead.)")
    write_outputs(records, args.out, flagged_only=args.flagged_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
