#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

MODE="${1:-main_all}"
if [ "$#" -gt 0 ]; then
  shift
fi

LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
LOG="${LOG_DIR}/wsl_${MODE}_latest.log"
STATUS="${LOG_DIR}/wsl_${MODE}_status.txt"
: > "${LOG}"
echo "RUNNING $(date '+%F %T')" > "${STATUS}"
exec > >(tee -a "${LOG}") 2>&1
trap 'code=$?; if [ "$code" -ne 0 ]; then echo "FAILED $code $(date "+%F %T")" > "${STATUS}"; fi' EXIT

source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-4}"
export NUMEXPR_MAX_THREADS="${NUMEXPR_MAX_THREADS:-4}"

run_config() {
  local label="$1"
  local config="$2"
  shift 2
  echo
  echo "===== ${label} (${config}) ====="
  python run_experiments.py --config "${config}" --resume "$@"
}

run_efficiency() {
  echo
  echo "===== Paper efficiency benchmark ====="
  python benchmark_efficiency.py --output-dir results/efficiency_benchmark --merge-existing "$@"
}

case "${MODE}" in
  tls40)
    run_config "TLS-40 main baselines" configs/tls40_s.yaml
    ;;
  quic40)
    run_config "QUIC-40 main baselines" configs/quic40_s.yaml
    ;;
  tls60)
    run_config "TLS-60 main baselines" configs/tls60_s.yaml
    ;;
  quic60)
    run_config "QUIC-60 main baselines" configs/quic60_s.yaml
    ;;
  main_all|all)
    run_config "TLS-40 main baselines" configs/tls40_s.yaml
    run_config "QUIC-40 main baselines" configs/quic40_s.yaml
    run_config "TLS-60 main baselines" configs/tls60_s.yaml
    run_config "QUIC-60 main baselines" configs/quic60_s.yaml
    ;;
  recent_all)
    run_config "Recent journal baselines" configs/recent_journal_baselines.yaml
    ;;
  sota_all)
    run_config "Adapted SOTA baselines" configs/sota_adapted.yaml
    ;;
  ablation_all)
    run_config "HSTA No Attention ablation" configs/hsta_no_attention.yaml
    run_config "HSTA FlashAttention position ablation" configs/hsta_flash_ablation.yaml
    ;;
  hsta_flash_all)
    run_config "HSTA FlashAttention main experiments" configs/hsta_flash.yaml
    run_config "HSTA No Attention ablation" configs/hsta_no_attention.yaml
    run_config "HSTA FlashAttention ablation experiments" configs/hsta_flash_ablation.yaml
    ;;
  efficiency)
    run_efficiency "$@"
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    echo "Available: tls40, quic40, tls60, quic60, main_all, recent_all, sota_all, ablation_all, hsta_flash_all, efficiency"
    exit 1
    ;;
esac

echo
echo "Finished: ${MODE} $(date '+%F %T')"
echo "Main results:       results/tls40_s, results/quic40_s, results/tls60_s, results/quic60_s"
echo "Recent baselines:   results/recent_journal_baselines"
echo "Adapted baselines:  results/sota_adapted"
echo "HSTA experiments:   results/hsta_flash, results/hsta_flash_ablation"
echo "Efficiency results: results/efficiency_benchmark"
echo "OK $(date '+%F %T')" > "${STATUS}"
