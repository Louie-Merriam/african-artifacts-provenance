#!/usr/bin/env bash
# run_haiku.sh - run the FULL pipeline with real Claude Haiku adjudication, locally.
#
# Why local: the model call needs YOUR Anthropic API key. Set it in your own
# shell; it is never shared with anyone. (The Cowork assistant cannot enter API
# keys on your behalf, which is why this step runs on your machine.)
#
# Usage:
#   export ANTHROPIC_API_KEY=sk-ant-...           # your key, your machine
#   RECORDS_CSV=sample_bm_export.csv bash run_haiku.sh
#
# Point RECORDS_CSV at any CSV exported from the BM collection site
# (the /api/_download export). Optional overrides: OUT=..., MODEL=...
set -euo pipefail

: "${ANTHROPIC_API_KEY:?ERROR: set ANTHROPIC_API_KEY first (export ANTHROPIC_API_KEY=sk-ant-...)}"
RECORDS_CSV="${RECORDS_CSV:-sample_bm_export.csv}"
OUT="${OUT:-out/haiku}"
MODEL="${MODEL:-claude-haiku-4-5-20251001}"

echo ">> ensuring the anthropic SDK is installed"
python3 -m pip install -q anthropic

echo ">> [1/2] extract + normalize: $RECORDS_CSV"
python3 bm_provenance_extractor.py csv "$RECORDS_CSV" --rules redflag_rules.json -o "${OUT}_records"

echo ">> [2/2] adjudicate with $MODEL (shortlisted records only)"
python3 bm_adjudicate.py --records "${OUT}_records.jsonl" --kb redflags_africa_patched.json \
        --model "$MODEL" -o "$OUT"

echo
echo ">> done:"
echo "   ${OUT}.csv               full adjudication"
echo "   ${OUT}_review_queue.jsonl  unfair + transactional, highest confidence first"
