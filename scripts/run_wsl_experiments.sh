#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
MODE="${1:-main}"
case "$MODE" in
  main)
    python run_experiments.py --config configs/compact_s.yaml --resume ;;
  all)
    python run_experiments.py --config configs/compact_s.yaml --resume
    python scripts/summarize_compact_results.py ;;
  *) echo "Usage: $0 {main|all}" >&2; exit 2 ;;
esac
