#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-main}"
source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
mkdir -p logs

case "$MODE" in
  main)
    # TLS60 和 QUIC60 的主比较，从第 1 轮开始，不复用旧结果。
    python run_experiments.py \
      --config configs/compact_s.yaml \
      --force --no-resume
    ;;
  ablation)
    # HSTA-CM 的 no-conv、no-mamba、no-attention 组件检查。
    python run_experiments.py \
      --config configs/hsta_cm_ablation_s.yaml \
      --force --no-resume
    ;;
  efficiency)
    # 只测用户要求的三个 batch size。
    python benchmark_efficiency.py \
      --configs configs/compact_s.yaml configs/hsta_cm_ablation_s.yaml \
      --output-dir results/efficiency_benchmark \
      --batch-sizes 1 8 32 \
      --seed 599
    ;;
  *)
    echo "Usage: $0 {main|ablation|efficiency}" >&2
    exit 2
    ;;
esac
