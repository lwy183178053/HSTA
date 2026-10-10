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
    python run_experiments.py --config configs/compact_s.yaml --resume --extend
    ;;
  small_tls|open_set_tls_seed599)
    # One deterministic TLS22-S small run with DFT-HSTA-open, its closed-set
    # unknown ablation, the no-DFT component ablation and retained baselines.
    python run_experiments.py \
      --config configs/compact_s.yaml \
      --output-dir results/open_set_tls_seed599 \
      --data-csv data/processed/datazoo_tls100_s_protocol_small_sampled.csv \
      --only \
        hsta_cm_dft_tls22_s_seed599 \
        hsta_cm_dft_closed_tls22_s_seed599 \
        hsta_cm_no_dft_tls22_s_seed599 \
        tcnet_tls22_s \
        netmamba_tls22_s \
        srvit_tls22_s \
        trafficaudio_tls22_s \
        bpfgnn_tls22_s \
      --resume --extend
    ;;
  small_quic|open_set_quic_seed599)
    # One deterministic QUIC22-S small run under the same open-set protocol.
    python run_experiments.py \
      --config configs/compact_s.yaml \
      --output-dir results/open_set_quic_seed599 \
      --data-csv data/processed/datazoo_quic100_s_protocol_small_sampled.csv \
      --only \
        hsta_cm_dft_quic22_s_seed599 \
        hsta_cm_dft_closed_quic22_s_seed599 \
        hsta_cm_no_dft_quic22_s_seed599 \
        tcnet_quic22_s \
        netmamba_quic22_s \
        srvit_quic22_s \
        trafficaudio_quic22_s \
        bpfgnn_quic22_s \
      --resume --extend
    ;;
  ablation|compact_ablation_s)
    python run_experiments.py --config configs/hsta_cm_ablation_s.yaml --resume --extend
    ;;
  efficiency)
    python benchmark_efficiency.py --output-dir results/efficiency_benchmark
    ;;
  *)
    echo "Usage: $0 {main|main_all|compact_s|small_tls|small_quic|ablation|efficiency}" >&2
    exit 2
    ;;
esac
