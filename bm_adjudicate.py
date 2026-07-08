#!/usr/bin/env python3
"""
bm_adjudicate.py
================
Cross-reference scraped British Museum object records against the Africa
unjust-acquisition knowledge base (redflags_africa.json), using a lightweight
LLM (Claude Haiku by default) to make an EVIDENCE-CITED judgment.

This replaces the numeric scoring system. The pipeline is:

   records (JSONL/CSV from bm_provenance_extractor.py)
        |
   [1] cheap deterministic SHORTLISTER
        -- a record advances only if it mentions a knowledge-base entity
           (incident / actor / channel / region / method alias).
        -- this keeps LLM cost down: most records never reach the model.
        |
   [2] LLM ADJUDICATION (Haiku)
        -- gets ONLY the KB entries that matched + the record text.
        -- must return strict JSON: category, matched_flags, evidence_quotes,
           confidence, rationale.
        -- "insufficient_evidence" is a required, respectable answer.
        |
   output: adjudicated.jsonl + adjudicated.csv (+ a human review queue)

The model never sees the whole knowledge base or invents history freely — it
weighs the supplied red flags against the supplied mitigating features and must
quote the record to justify any "unfair" call.

Usage
-----
  # Dry run with no API key (deterministic stub, good for testing the plumbing):
  python bm_adjudicate.py --records out/sample.jsonl --kb redflags_africa.json \
        --mock -o out/adjudicated

  # Real run with Haiku (needs: pip install anthropic ; export ANTHROPIC_API_KEY=...):
  python bm_adjudicate.py --records out/benin.jsonl --kb redflags_africa.json \
        --model claude-haiku-4-5 -o out/benin_adjudicated

  # Swap models: --model gpt-4o-mini (set OPENAI_API_KEY) or any provider you wire in.
"""

from __future__ import annotations

import argparse
import csv as csvmod
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

csvmod.field_size_limit(10_000_000)
LOG = logging.getLogger("adjudicate")

RECORD_TEXT_FIELDS = [
    "title", "object_type", "culture", "production_place", "findspot",
    "acquisition_from", "acquisition_finder", "acquisition_excavator",
    "acquisition_previous", "acquisition_date", "acquisition_notes",
    "provenance_text",
]

VALID_CATEGORIES = {"unfair", "transactional", "fair", "insufficient_evidence"}


# ---------------------------------------------------------------------------
# Knowledge base + matching
# ---------------------------------------------------------------------------

class KnowledgeBase:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.tables = {
            "incidents": data.get("incidents", []),
            "actors": data.get("actors", []),
            "channels": data.get("channels", []),
            "regions": data.get("regions", []),
            "methods": data.get("methods", []),
        }
        self.mitigating = data.get("mitigating_features", [])
        # Pre-compile alias -> (table, entry) index. Word-boundary regexes.
        self._index: List[Tuple[re.Pattern, str, Dict[str, Any]]] = []
        for table, entries in self.tables.items():
            for entry in entries:
                aliases = self._aliases_for(table, entry)
                for alias in aliases:
                    pat = re.compile(r"(?<![\w])" + re.escape(alias) + r"(?![\w])", re.I)
                    self._index.append((pat, table, entry))
        # mitigating phrases
        self._mit_index: List[Tuple[re.Pattern, Dict[str, Any]]] = []
        for m in self.mitigating:
            for ph in m.get("phrases", []):
                self._mit_index.append((re.compile(re.escape(ph), re.I), m))

    @staticmethod
    def _aliases_for(table: str, entry: Dict[str, Any]) -> List[str]:
        out = []
        if entry.get("name"):
            out.append(entry["name"])
        out.extend(entry.get("aliases", []))
        out.extend(entry.get("culture_terms", []))
        if table == "methods":
            out.extend(entry.get("phrases", []))
        # de-dupe, drop very short/noisy aliases
        seen, clean = set(), []
        for a in out:
            a = a.strip()
            if len(a) < 3 or a.lower() in seen:
                continue
            seen.add(a.lower())
            clean.append(a)
        return clean

    def match(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Return matched KB entries grouped by table, plus mitigating hits."""
        hits: Dict[str, List[Dict[str, Any]]] = {k: [] for k in self.tables}
        seen_ids = set()
        for pat, table, entry in self._index:
            if pat.search(text):
                key = (table, entry.get("id"))
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                hits[table].append(entry)
        mit = []
        seen_m = set()
        for pat, m in self._mit_index:
            if pat.search(text) and m.get("id") not in seen_m:
                seen_m.add(m.get("id"))
                mit.append(m)
        hits["mitigating"] = mit
        return hits


def record_text(rec: Dict[str, Any]) -> str:
    return " ‖ ".join(str(rec.get(f, "") or "") for f in RECORD_TEXT_FIELDS).strip()


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a provenance research analyst assessing whether a museum object \
was likely acquired through colonial looting/theft, or instead through a fair or ordinary \
transaction. You are rigorous and fair-minded. Many African objects in Western museums were \
acquired legitimately; do not assume guilt. Judge ONLY from the object record provided and the \
red-flag / mitigating reference entries provided. Do not invent facts not present in either.

You must return STRICT JSON with these keys:
  "category": one of "unfair", "transactional", "fair", "insufficient_evidence"
  "matched_flags": list of knowledge-base entry ids that genuinely apply
  "evidence_quotes": list of SHORT verbatim quotes copied from the object record that justify your call
  "confidence": "low" | "medium" | "high"
  "rationale": 1-3 sentences explaining the call, referencing the matched flags and any mitigating factors

Rules:
- "unfair" requires concrete evidence in the record linking the object to a looting incident, a \
watch-listed actor/channel, or explicit spoils language. Cite the quote(s).
- If a mitigating feature (documented clean provenance, consensual gift, arm's-length modern sale not \
tracing to a flagged channel) outweighs the flags, use "transactional" or "fair".
- If the record is too thin to tell, use "insufficient_evidence" with empty evidence_quotes. This is \
an acceptable and expected answer; do not guess.
- evidence_quotes MUST be substrings of the record. Never fabricate a quote.

LAUNDERED PROVENANCE (important): colonial loot was routinely sold through the market for decades after seizure, so a later arm's-length or modern sale does NOT clear an object if an earlier owner in its chain is a watch-listed loot dealer or auction house (any entity supplied under 'actors' or 'channels'). When a court or ritual object of a looted culture (e.g. a Benin brass/ivory, Asante gold regalia, an Ethiopian tabot/cross, a Kongo nkisi) has a watch-listed dealer anywhere in its provenance, treat it as "unfair" UNLESS the record documents legitimate acquisition dated BEFORE the relevant looting event. Do not let a clean-looking later sale outweigh a flagged dealer earlier in the chain."""


def build_user_prompt(rec: Dict[str, Any], hits: Dict[str, List[Dict[str, Any]]]) -> str:
    def brief(entry: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        return {k: entry[k] for k in keys if k in entry}

    kb_context = {
        "incidents": [brief(e, ["id", "name", "date_window", "summary", "museum_signals"]) for e in hits["incidents"]],
        "actors": [brief(e, ["id", "name", "role", "why_flag"]) for e in hits["actors"]],
        "channels": [brief(e, ["id", "name", "type", "why_flag"]) for e in hits["channels"]],
        "regions": [brief(e, ["id", "name", "date_windows", "why_flag"]) for e in hits["regions"]],
        "methods": [brief(e, ["id", "label", "why_flag"]) for e in hits["methods"]],
        "mitigating_features": [brief(e, ["id", "label", "effect"]) for e in hits.get("mitigating", [])],
    }
    record_view = {f: rec.get(f, "") for f in (["object_id"] + RECORD_TEXT_FIELDS) if rec.get(f)}
    return (
        "OBJECT RECORD (the only text you may quote):\n"
        + json.dumps(record_view, ensure_ascii=False, indent=2)
        + "\n\nMATCHED KNOWLEDGE-BASE ENTRIES (red flags + mitigating features that mention this record):\n"
        + json.dumps(kb_context, ensure_ascii=False, indent=2)
        + "\n\nReturn only the JSON object."
    )


# ---------------------------------------------------------------------------
# Model adapters
# ---------------------------------------------------------------------------

# Forcing a tool/function schema guarantees the model returns STRUCTURED, valid
# JSON — it cannot emit broken JSON (unescaped quotes etc.) the way free-text can.
ASSESSMENT_TOOL = {
    "name": "submit_assessment",
    "description": "Submit the provenance assessment for this object.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string",
                         "enum": ["unfair", "transactional", "fair", "insufficient_evidence"]},
            "matched_flags": {"type": "array", "items": {"type": "string"},
                              "description": "knowledge-base entry ids that genuinely apply"},
            "evidence_quotes": {"type": "array", "items": {"type": "string"},
                                "description": "short verbatim quotes copied from the object record"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "rationale": {"type": "string"},
        },
        "required": ["category", "matched_flags", "evidence_quotes", "confidence", "rationale"],
    },
}


def call_anthropic(system: str, user: str, model: str) -> str:
    import anthropic  # type: ignore
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=900,
        temperature=0,
        system=system,
        tools=[ASSESSMENT_TOOL],
        tool_choice={"type": "tool", "name": "submit_assessment"},
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if getattr(block, "type", "") == "tool_use":
            return json.dumps(block.input)  # block.input is already a dict -> always valid
    # fallback: some models may still answer as text
    return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")


def call_openai(system: str, user: str, model: str) -> str:
    from openai import OpenAI  # type: ignore
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=700,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


def mock_adjudicate(rec: Dict[str, Any], hits: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Deterministic stand-in so the pipeline runs without an API key.
    Mirrors the decision logic we want the LLM to apply, crudely."""
    text = record_text(rec).lower()
    flags = [e["id"] for t in ("incidents", "actors", "channels", "regions", "methods")
             for e in hits[t]]
    mit = [m["id"] for m in hits.get("mitigating", [])]
    spoils = any(w in text for w in
                 ["loot", "plunder", "spoils", "punitive", "seized", "captured", "taken during", "prize"])
    strong = bool(hits["incidents"] or hits["actors"] or hits["channels"]) and (spoils or hits["actors"])
    quotes = []
    for w in ["punitive expedition", "spoils of war", "looted", "prize", "presented by", "captured"]:
        m = re.search(r"[^‖]*" + re.escape(w) + r"[^‖]*", text)
        if m:
            quotes.append(m.group(0).strip()[:120])
    if strong and not mit:
        cat, conf = "unfair", "medium"
    elif flags and mit:
        cat, conf = "transactional", "low"
    elif flags:
        cat, conf = "transactional", "low"
    else:
        cat, conf = "insufficient_evidence", "low"
    return {
        "category": cat,
        "matched_flags": flags,
        "evidence_quotes": quotes[:3],
        "confidence": conf,
        "rationale": f"[MOCK] matched {len(flags)} flag(s), {len(mit)} mitigating; "
                     f"spoils_language={spoils}.",
    }


def parse_model_json(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        raw = m.group(0)
    obj = json.loads(raw)
    if obj.get("category") not in VALID_CATEGORIES:
        obj["category"] = "insufficient_evidence"
    obj.setdefault("matched_flags", [])
    obj.setdefault("evidence_quotes", [])
    obj.setdefault("confidence", "low")
    obj.setdefault("rationale", "")
    return obj


def validate_quotes(rec: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Drop any 'evidence quote' that is not actually a substring of the record —
    guards against the model fabricating evidence."""
    hay = record_text(rec).lower()
    kept = [q for q in result.get("evidence_quotes", []) if q and len(q.strip()) >= 4 and q.lower()[:60] in hay]
    dropped = len(result.get("evidence_quotes", [])) - len(kept)
    result["evidence_quotes"] = kept
    if dropped and result["category"] == "unfair" and not kept:
        # an "unfair" call with no surviving evidence is downgraded
        result["category"] = "insufficient_evidence"
        result["rationale"] = "[downgraded: fabricated/unverifiable quotes removed] " + result.get("rationale", "")
    return result


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def load_records(path: str) -> List[Dict[str, Any]]:
    if path.endswith(".jsonl"):
        return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    if path.endswith(".json"):
        d = json.load(open(path, encoding="utf-8"))
        return d if isinstance(d, list) else [d]
    # csv
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csvmod.DictReader(fh))


def adjudicate_one(rec: Dict[str, Any], kb: KnowledgeBase, backend: str, model: str) -> Optional[Dict[str, Any]]:
    text = record_text(rec)
    hits = kb.match(text)
    shortlisted = any(hits[t] for t in ("incidents", "actors", "channels", "regions", "methods"))
    if not shortlisted:
        return None  # never reaches the LLM
    if backend == "mock":
        result = mock_adjudicate(rec, hits)
    else:
        system, user = SYSTEM_PROMPT, build_user_prompt(rec, hits)
        caller = call_anthropic if backend == "anthropic" else call_openai
        raw = _retry(lambda: caller(system, user, model))
        if raw is None:
            result = {"category": "insufficient_evidence", "matched_flags": [],
                      "evidence_quotes": [], "confidence": "low",
                      "rationale": "[error: model call failed]"}
        else:
            try:
                result = parse_model_json(raw)
            except Exception as e:  # noqa: BLE001
                LOG.warning("Bad JSON from model for %s: %s", rec.get("object_id"), e)
                result = {"category": "insufficient_evidence", "matched_flags": [],
                          "evidence_quotes": [], "confidence": "low",
                          "rationale": "[error: unparseable model output]"}
    result = validate_quotes(rec, result)
    result["object_id"] = rec.get("object_id", "")
    result["shortlist_matches"] = {t: [e["id"] for e in hits[t]] for t in kb.tables}
    result["_record"] = rec
    return result


def _retry(fn, tries: int = 4):
    delay = 2.0
    for i in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            LOG.warning("model call attempt %d/%d failed: %s", i, tries, e)
            if i == tries:
                return None
            time.sleep(delay)
            delay *= 2
    return None


OUT_COLUMNS = ["object_id", "category", "confidence", "matched_flags",
               "evidence_quotes", "rationale", "source_url"]


def write_outputs(results: List[Dict[str, Any]], out_prefix: str) -> None:
    os.makedirs(os.path.dirname(out_prefix) or ".", exist_ok=True)
    with open(out_prefix + ".jsonl", "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out_prefix + ".csv", "w", newline="", encoding="utf-8") as fh:
        w = csvmod.DictWriter(fh, fieldnames=OUT_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow({
                "object_id": r.get("object_id", ""),
                "category": r.get("category", ""),
                "confidence": r.get("confidence", ""),
                "matched_flags": "; ".join(r.get("matched_flags", [])),
                "evidence_quotes": " | ".join(r.get("evidence_quotes", [])),
                "rationale": r.get("rationale", ""),
                "source_url": (r.get("_record") or {}).get("source_url", ""),
            })
    # human review queue: unfair + transactional, highest-confidence first
    order = {"high": 0, "medium": 1, "low": 2}
    queue = sorted([r for r in results if r.get("category") in ("unfair", "transactional")],
                   key=lambda r: (r.get("category") != "unfair", order.get(r.get("confidence"), 3)))
    with open(out_prefix + "_review_queue.jsonl", "w", encoding="utf-8") as fh:
        for r in queue:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    c = Counter(r.get("category") for r in results)
    LOG.info("Adjudicated %d shortlisted records: %s", len(results), dict(c))
    LOG.info("Review queue: %d records -> %s_review_queue.jsonl", len(queue), out_prefix)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--records", required=True, help="JSONL/CSV from bm_provenance_extractor.py")
    p.add_argument("--kb", default="redflags_africa.json", help="knowledge-base JSON")
    p.add_argument("-o", "--out", default="out/adjudicated")
    p.add_argument("--model", default="claude-haiku-4-5")
    p.add_argument("--backend", choices=["auto", "anthropic", "openai", "mock"], default="auto")
    p.add_argument("--mock", action="store_true", help="shortcut for --backend mock")
    p.add_argument("--limit", type=int, default=0, help="cap records (0 = all)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s")

    backend = "mock" if args.mock else args.backend
    if backend == "auto":
        if args.model.startswith("gpt") or args.model.startswith("o"):
            backend = "openai"
        else:
            backend = "anthropic"
    if backend == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        LOG.warning("No ANTHROPIC_API_KEY set — falling back to --mock. "
                    "Install `anthropic` and set the key for real adjudication.")
        backend = "mock"
    if backend == "openai" and not os.environ.get("OPENAI_API_KEY"):
        LOG.warning("No OPENAI_API_KEY set — falling back to --mock.")
        backend = "mock"

    kb = KnowledgeBase(json.load(open(args.kb, encoding="utf-8")))
    records = load_records(args.records)
    if args.limit:
        records = records[:args.limit]
    LOG.info("Loaded %d records; backend=%s model=%s", len(records), backend, args.model)

    results, shortlisted = [], 0
    for i, rec in enumerate(records, 1):
        res = adjudicate_one(rec, kb, backend, args.model)
        if res is None:
            continue
        shortlisted += 1
        results.append(res)
        if backend != "mock":
            time.sleep(0.2)  # be gentle on the API
        if i % 200 == 0:
            LOG.info("processed %d / %d (shortlisted %d)", i, len(records), shortlisted)

    LOG.info("Shortlisted %d / %d records for the model (the rest never cost a call).",
             shortlisted, len(records))
    write_outputs(results, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
