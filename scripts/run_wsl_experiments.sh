#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-main}"
source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
mkdir -p logs

case "$MODE" in
  main|main_all|compact_s)
    python run_experiments.py --config configs/compact_s.yaml --resume
    ;;
  ablation|compact_ablation_s)
    python run_experiments.py --config configs/hsta_cm_ablation_s.yaml --resume
    ;;
  efficiency)
    python benchmark_efficiency.py --output-dir results/efficiency_benchmark
    ;;
  *)
    echo "Usage: $0 {main|ablation|efficiency}" >&2
    exit 2
    ;;
esac
