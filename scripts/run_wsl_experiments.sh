#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
MODE="${1:-main}"
case "$MODE" in
  main)
    python run_experiments.py --config configs/compact_s.yaml --force --no-resume ;;
  ablation)
    python run_experiments.py --config configs/hsta_cm_ablation_s.yaml --force --no-resume ;;
  efficiency)
    python benchmark_efficiency.py --configs configs/compact_s.yaml \
      --only hsta_cm_open_tls60_seed599 hsta_cm_open_quic60_seed599 \
      --output-dir results/efficiency_benchmark --batch-sizes 1 8 32 --seed 599 ;;
  all)
    bash scripts/run_wsl_experiments.sh main
    bash scripts/run_wsl_experiments.sh ablation
    bash scripts/run_wsl_experiments.sh efficiency
    python scripts/summarize_compact_results.py ;;
  *) echo "Usage: $0 {main|ablation|efficiency|all}" >&2; exit 2 ;;
esac
