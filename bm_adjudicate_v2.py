#!/usr/bin/env python3
"""bm_adjudicate_v2 — production runner wrapping bm_adjudicate.py.

Fixes for the full-corpus run:
  1. --gate strict (default): shortlist on incidents/actors/channels/methods only.
     Bare region hits no longer send a record to the model (on an all-Africa corpus
     the regions table matches ~90% of records: 17,779/19,994 broad vs 10,458 strict).
     Regions still reach the model as context whenever another table also hits.
     Use --gate broad for the old behaviour.
  2. Incremental writes + --resume: every verdict is appended to <out>.stream.jsonl
     the moment it exists. Interrupt/crash loses nothing; re-run with the same -o
     and it skips finished records and re-attaches to submitted batches.
  3. --mode batch (default): Anthropic Message Batches API — half price, no
     long-lived HTTP connections (fixes the retry/timeout storms), no babysitting.
     --mode serial keeps the old per-call loop (with incremental writes).
  4. Records whose model call failed are written with rationale
     '[error: model call failed]' — re-running with --retry-errors redoes them.

Usage (on the machine with ANTHROPIC_API_KEY set):
  python3 bm_adjudicate_v2.py --records analysis_out/full_records.jsonl \
      --kb redflags_africa_patched.json --model claude-haiku-4-5 -o out/full_adjudicated
  # add --dry-run first to see shortlist counts and cost estimate without submitting
"""
import argparse, json, logging, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bm_adjudicate", os.path.join(HERE, "bm_adjudicate.py"))
adj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adj)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
LOG = logging.getLogger("adjudicate_v2")

GATES = {"strict": ("incidents", "actors", "channels", "methods"),
         "broad": ("incidents", "actors", "channels", "regions", "methods")}
ERROR_MARK = "[error: model call failed]"


def build_result(rec, hits, kb, raw):
    if raw is None:
        result = {"category": "insufficient_evidence", "matched_flags": [],
                  "evidence_quotes": [], "confidence": "low", "rationale": ERROR_MARK}
    else:
        try:
            result = adj.parse_model_json(raw)
        except Exception as e:  # noqa: BLE001
            LOG.warning("Bad JSON from model for %s: %s", rec.get("object_id"), e)
            result = {"category": "insufficient_evidence", "matched_flags": [],
                      "evidence_quotes": [], "confidence": "low",
                      "rationale": "[error: unparseable model output]"}
    result = adj.validate_quotes(rec, result)
    result["object_id"] = rec.get("object_id", "")
    result["shortlist_matches"] = {t: [e["id"] for e in hits[t]] for t in kb.tables}
    result["_record"] = rec
    return result


def make_matcher(kb, kb_raw):
    """Fast multi-pattern replacement for kb.match (same word-boundary semantics).
    Falls back to kb.match if pyahocorasick is unavailable."""
    try:
        import ahocorasick
    except ImportError:
        LOG.warning("pyahocorasick not installed — using the slow per-alias matcher "
                    "(pip install pyahocorasick to speed this up ~100x)")
        return kb.match
    A = ahocorasick.Automaton()
    alias_map = {}
    tabs = list(kb.tables) + [("mitigating_features", "mitigating")]
    for t in kb.tables:
        for e in kb_raw.get(t, []):
            for a in adj.KnowledgeBase._aliases_for(t, e):
                alias_map.setdefault(a.lower(), []).append((t, e))
    for m in kb_raw.get("mitigating_features", []):
        for a in adj.KnowledgeBase._aliases_for("mitigating_features", m):
            alias_map.setdefault(a.lower(), []).append(("mitigating", m))
    for a in alias_map:
        A.add_word(a, a)
    A.make_automaton()

    def match(text):
        low = text.lower()
        hits = {k: [] for k in kb.tables}
        hits["mitigating"] = []
        seen = set()
        for end, a in A.iter(low):
            s = end - len(a) + 1
            b = low[s - 1] if s > 0 else " "
            c = low[end + 1] if end + 1 < len(low) else " "
            if (b.isalnum() or b == "_") or (c.isalnum() or c == "_"):
                continue
            for t, e in alias_map[a]:
                key = (t, e.get("id"))
                if key in seen:
                    continue
                seen.add(key)
                hits[t].append(e)
        return hits
    return match


def shortlist(records, matcher, tables):
    out = []
    for i, rec in enumerate(records):
        hits = matcher(adj.record_text(rec))
        if any(hits[t] for t in tables):
            out.append((i, rec, hits))
        if (i + 1) % 5000 == 0:
            LOG.info("shortlisting %d / %d (kept %d)", i + 1, len(records), len(out))
    return out


def load_stream(path, retry_errors):
    done = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            cid = r.get("_custom_id")
            if not cid:
                continue
            if retry_errors and r.get("rationale") == ERROR_MARK:
                continue
            done[cid] = r
    return done


def stream_write(fh, cid, result):
    result = dict(result)
    result["_custom_id"] = cid
    fh.write(json.dumps(result, ensure_ascii=False) + "\n")
    fh.flush()


def batch_params(rec, hits, model):
    return {"model": model, "max_tokens": 900, "temperature": 0,
            "system": adj.SYSTEM_PROMPT,
            "tools": [adj.ASSESSMENT_TOOL],
            "tool_choice": {"type": "tool", "name": "submit_assessment"},
            "messages": [{"role": "user", "content": adj.build_user_prompt(rec, hits)}]}


def extract_raw(message) -> str:
    for block in message.content:
        if getattr(block, "type", "") == "tool_use":
            return json.dumps(block.input)
    return "".join(getattr(b, "text", "") for b in message.content
                   if getattr(b, "type", "") == "text")


def run_batch(pending, kb, model, out_prefix, poll_s):
    import anthropic
    client = anthropic.Anthropic()
    state_path = out_prefix + ".batches.json"
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"batches": []}
    # only IN-FLIGHT (uncollected) batches block resubmission; for collected batches
    # the stream file is the source of truth, so records stripped from the stream
    # (e.g. the quote-bug requeue) get submitted again.
    submitted = {cid for b in state["batches"] if not b.get("collected")
                 for cid in b["custom_ids"]}
    by_cid = {cid: (rec, hits) for cid, rec, hits in pending}

    todo = [(cid, rec, hits) for cid, rec, hits in pending if cid not in submitted]
    CHUNK = 10000
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        reqs = [{"custom_id": cid, "params": batch_params(rec, hits, model)}
                for cid, rec, hits in chunk]
        b = client.messages.batches.create(requests=reqs)
        state["batches"].append({"id": b.id, "custom_ids": [c for c, _, _ in chunk], "collected": False})
        json.dump(state, open(state_path, "w"), indent=1)
        LOG.info("submitted batch %s (%d requests)", b.id, len(chunk))

    stream_path = out_prefix + ".stream.jsonl"
    fh = open(stream_path, "a", encoding="utf-8")
    while any(not b["collected"] for b in state["batches"]):
        for b in state["batches"]:
            if b["collected"]:
                continue
            st = client.messages.batches.retrieve(b["id"])
            LOG.info("batch %s: %s %s", b["id"], st.processing_status,
                     getattr(st, "request_counts", ""))
            if st.processing_status != "ended":
                continue
            n_ok = n_err = 0
            for entry in client.messages.batches.results(b["id"]):
                cid = entry.custom_id
                if cid not in by_cid:
                    continue
                rec, hits = by_cid[cid]
                if entry.result.type == "succeeded":
                    raw = extract_raw(entry.result.message); n_ok += 1
                else:
                    LOG.warning("batch entry %s -> %s", cid, entry.result.type)
                    raw = None; n_err += 1
                stream_write(fh, cid, build_result(rec, hits, kb, raw))
            b["collected"] = True
            json.dump(state, open(state_path, "w"), indent=1)
            LOG.info("collected batch %s: %d ok, %d errored", b["id"], n_ok, n_err)
        if any(not b["collected"] for b in state["batches"]):
            time.sleep(poll_s)
    fh.close()


def run_serial(pending, kb, model, out_prefix):
    stream_path = out_prefix + ".stream.jsonl"
    fh = open(stream_path, "a", encoding="utf-8")
    for n, (cid, rec, hits) in enumerate(pending, 1):
        user = adj.build_user_prompt(rec, hits)
        raw = adj._retry(lambda: adj.call_anthropic(adj.SYSTEM_PROMPT, user, model))
        stream_write(fh, cid, build_result(rec, hits, kb, raw))
        time.sleep(0.2)
        if n % 100 == 0:
            LOG.info("serial: %d / %d done", n, len(pending))
    fh.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--kb", default=os.path.join(HERE, "redflags_africa_patched.json"))
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--gate", choices=list(GATES), default="strict")
    ap.add_argument("--mode", choices=["batch", "serial"], default="batch")
    ap.add_argument("-o", "--out", default="out/full_adjudicated")
    ap.add_argument("--poll-seconds", type=int, default=60)
    ap.add_argument("--retry-errors", action="store_true",
                    help="redo records previously written with a model-call error")
    ap.add_argument("--dry-run", action="store_true",
                    help="report shortlist counts + cost estimate, submit nothing")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

    kb_raw = json.load(open(a.kb, encoding="utf-8"))
    kb = adj.KnowledgeBase(kb_raw)
    records = adj.load_records(a.records)
    LOG.info("loaded %d records; gate=%s kb=%s", len(records), a.gate, a.kb)

    listed = shortlist(records, make_matcher(kb, kb_raw), GATES[a.gate])
    LOG.info("shortlisted %d / %d records (gate=%s)", len(listed), len(records), a.gate)
    est_std, est_batch = len(listed) * 0.0033, len(listed) * 0.0016
    LOG.info("cost estimate: ~$%.0f standard / ~$%.0f batch", est_std, est_batch)
    if a.dry_run:
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        LOG.error("ANTHROPIC_API_KEY not set — aborting (nothing submitted).")
        return 1

    done = load_stream(a.out + ".stream.jsonl", a.retry_errors)
    pending = [(f"i{idx}", rec, hits) for idx, rec, hits in listed if f"i{idx}" not in done]
    LOG.info("%d already done in stream; %d to run", len(done), len(pending))

    if pending:
        (run_batch if a.mode == "batch" else run_serial)(
            *((pending, kb, a.model, a.out, a.poll_seconds) if a.mode == "batch"
              else (pending, kb, a.model, a.out)))

    # final assembly: stream -> ordered, deduped outputs + review queue
    done = load_stream(a.out + ".stream.jsonl", retry_errors=False)
    order = {f"i{idx}": idx for idx, _, _ in listed}
    results = [done[c] for c in sorted(done, key=lambda c: order.get(c, 1 << 30)) if c in order]
    adj.write_outputs(results, a.out)
    queue = [r for r in results if r.get("category") in ("unfair", "transactional")]
    rank = {"high": 0, "medium": 1, "low": 2}
    queue.sort(key=lambda r: (0 if r.get("category") == "unfair" else 1,
                              rank.get(r.get("confidence"), 3)))
    with open(a.out + "_review_queue.jsonl", "w", encoding="utf-8") as f:
        for r in queue:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    c = Counter(r.get("category") for r in results)
    errs = sum(1 for r in results if r.get("rationale") == ERROR_MARK)
    LOG.info("DONE: %s | model-call errors: %d (re-run with --retry-errors) | review queue: %d",
             dict(c), errs, len(queue))
    return 0


if __name__ == "__main__":
    sys.exit(main())
