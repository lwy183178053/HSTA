#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

MODE="${1:-all}"
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
trap 'code=$?; if [ "$code" -ne 0 ]; then echo "FAILED ${code} $(date '"'"'+%F %T'"'"')" > "${STATUS}"; fi' EXIT

source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-4}"
export NUMEXPR_MAX_THREADS="${NUMEXPR_MAX_THREADS:-4}"
TRANSFER_CONFIG="configs/transfer_s.yaml"
SOTA_CONFIG="configs/sota_adapted.yaml"
ABLATION_CONFIG="configs/ablation_s.yaml"
STACK_TLS40_EXPS=(
  hybrid_mm_mlp_a_mlp_2block_tls40_s_seed42
  hybrid_mm_mlp_a_mlp_4block_tls40_s_seed42
)
STACK_QUIC40_EXPS=(
  hybrid_mm_mlp_a_mlp_2block_quic40_s_seed42
  hybrid_mm_mlp_a_mlp_4block_quic40_s_seed42
)
STACK_TLS60_EXPS=(
  hybrid_mm_mlp_a_mlp_2block_tls60_s_seed42
  hybrid_mm_mlp_a_mlp_4block_tls60_s_seed42
)
STACK_QUIC60_EXPS=(
  hybrid_mm_mlp_a_mlp_2block_quic60_s_seed42
  hybrid_mm_mlp_a_mlp_4block_quic60_s_seed42
)
SOTA_TLS40_EXPS=(
  30pkttcnet_adapted_tls40_s_seed42
  30pkttcnet_adapted_tls40_s_seed2025
  30pkttcnet_adapted_tls40_s_seed3407
  netmamba_adapted_tls40_s_seed42
  netmamba_adapted_tls40_s_seed2025
  netmamba_adapted_tls40_s_seed3407
)
SOTA_QUIC40_EXPS=(
  30pkttcnet_adapted_quic40_s_seed42
  30pkttcnet_adapted_quic40_s_seed2025
  30pkttcnet_adapted_quic40_s_seed3407
  netmamba_adapted_quic40_s_seed42
  netmamba_adapted_quic40_s_seed2025
  netmamba_adapted_quic40_s_seed3407
)
SOTA_TLS60_EXPS=(
  30pkttcnet_adapted_tls60_s_seed42
  30pkttcnet_adapted_tls60_s_seed2025
  30pkttcnet_adapted_tls60_s_seed3407
  netmamba_adapted_tls60_s_seed42
  netmamba_adapted_tls60_s_seed2025
  netmamba_adapted_tls60_s_seed3407
)
SOTA_QUIC60_EXPS=(
  30pkttcnet_adapted_quic60_s_seed42
  30pkttcnet_adapted_quic60_s_seed2025
  30pkttcnet_adapted_quic60_s_seed3407
  netmamba_adapted_quic60_s_seed42
  netmamba_adapted_quic60_s_seed2025
  netmamba_adapted_quic60_s_seed3407
)
SOTA_ALL_EXPS=(
  "${SOTA_TLS40_EXPS[@]}"
  "${SOTA_QUIC40_EXPS[@]}"
  "${SOTA_TLS60_EXPS[@]}"
  "${SOTA_QUIC60_EXPS[@]}"
)
ABLATION_TLS40_EXPS=()
ABLATION_QUIC40_EXPS=()
ABLATION_TLS60_EXPS=()
ABLATION_QUIC60_EXPS=()
for variant in no_attention attention_middle attention_front; do
  for seed in 42 2025 3407; do
    ABLATION_TLS40_EXPS+=("ablation_${variant}_tls40_s_seed${seed}")
    ABLATION_QUIC40_EXPS+=("ablation_${variant}_quic40_s_seed${seed}")
    ABLATION_TLS60_EXPS+=("ablation_${variant}_tls60_s_seed${seed}")
    ABLATION_QUIC60_EXPS+=("ablation_${variant}_quic60_s_seed${seed}")
  done
done
ABLATION_ALL_EXPS=(
  "${ABLATION_TLS40_EXPS[@]}"
  "${ABLATION_QUIC40_EXPS[@]}"
  "${ABLATION_TLS60_EXPS[@]}"
  "${ABLATION_QUIC60_EXPS[@]}"
)

run_config() {
  local name="$1"
  local config="$2"
  shift 2
  echo
  echo "============================================================"
  echo "${name}"
  echo "Config: ${config}"
  echo "Started: $(date '+%F %T')"
  echo "============================================================"
  python run_experiments.py --config "${config}" --resume "$@"
  echo "Finished: $(date '+%F %T')"
}

run_zero_shot() {
  local name="$1"
  local config="$2"
  shift 2
  echo
  echo "============================================================"
  echo "${name}"
  echo "Config: ${config}"
  echo "Started: $(date '+%F %T')"
  echo "============================================================"
  python run_experiments.py --config "${config}" --resume "$@"
  echo "Finished: $(date '+%F %T')"
}

run_efficiency() {
  local name="$1"
  shift
  echo
  echo "============================================================"
  echo "${name}"
  echo "Started: $(date '+%F %T')"
  echo "============================================================"
  python benchmark_efficiency.py "$@"
  echo "Finished: $(date '+%F %T')"
}

case "${MODE}" in
  tls)
    run_config "TLS40 experiments" "configs/tls40_s.yaml"
    ;;
  quic)
    run_config "QUIC40 experiments" "configs/quic40_s.yaml"
    ;;
  tls60)
    run_config "TLS60 experiments" "configs/tls60_s.yaml"
    ;;
  quic60)
    run_config "QUIC60 experiments" "configs/quic60_s.yaml"
    ;;
  ablation40)
    run_config "TLS40/QUIC40 ablation experiments, seeds 42/2025/3407" "${ABLATION_CONFIG}" --only "${ABLATION_TLS40_EXPS[@]}" "${ABLATION_QUIC40_EXPS[@]}"
    ;;
  ablation60)
    run_config "TLS60/QUIC60 ablation experiments, seeds 42/2025/3407" "${ABLATION_CONFIG}" --only "${ABLATION_TLS60_EXPS[@]}" "${ABLATION_QUIC60_EXPS[@]}"
    ;;
  ablation|ablation_all)
    run_config "TLS40/QUIC40/TLS60/QUIC60 ablation experiments, seeds 42/2025/3407" "${ABLATION_CONFIG}" --only "${ABLATION_ALL_EXPS[@]}"
    ;;
  seed60)
    run_config "1/2 TLS60 seed robustness experiments" "configs/tls60_s.yaml" --only transformer_5layer_tls60_s_seed2025 hybrid_mm_mlp_a_mlp_tls60_s_seed2025 transformer_5layer_tls60_s_seed3407 hybrid_mm_mlp_a_mlp_tls60_s_seed3407
    run_config "2/2 QUIC60 seed robustness experiments" "configs/quic60_s.yaml" --only transformer_5layer_quic60_s_seed2025 hybrid_mm_mlp_a_mlp_quic60_s_seed2025 transformer_5layer_quic60_s_seed3407 hybrid_mm_mlp_a_mlp_quic60_s_seed3407
    ;;
  seed40)
    run_config "1/2 TLS40 seed robustness experiments" "configs/tls40_s.yaml" --only transformer_5layer_tls40_s_seed2025 hybrid_mm_mlp_a_mlp_tls40_s_seed2025 transformer_5layer_tls40_s_seed3407 hybrid_mm_mlp_a_mlp_tls40_s_seed3407
    run_config "2/2 QUIC40 seed robustness experiments" "configs/quic40_s.yaml" --only transformer_5layer_quic40_s_seed2025 hybrid_mm_mlp_a_mlp_quic40_s_seed2025 transformer_5layer_quic40_s_seed3407 hybrid_mm_mlp_a_mlp_quic40_s_seed3407
    ;;
  stack40)
    run_config "1/2 TLS40 hybrid block stacking experiments" "configs/tls40_s.yaml" --only "${STACK_TLS40_EXPS[@]}"
    run_config "2/2 QUIC40 hybrid block stacking experiments" "configs/quic40_s.yaml" --only "${STACK_QUIC40_EXPS[@]}"
    ;;
  stack60)
    run_config "1/2 TLS60 hybrid block stacking experiments" "configs/tls60_s.yaml" --only "${STACK_TLS60_EXPS[@]}"
    run_config "2/2 QUIC60 hybrid block stacking experiments" "configs/quic60_s.yaml" --only "${STACK_QUIC60_EXPS[@]}"
    ;;
  stack_all)
    run_config "1/4 TLS40 hybrid block stacking experiments" "configs/tls40_s.yaml" --only "${STACK_TLS40_EXPS[@]}"
    run_config "2/4 QUIC40 hybrid block stacking experiments" "configs/quic40_s.yaml" --only "${STACK_QUIC40_EXPS[@]}"
    run_config "3/4 TLS60 hybrid block stacking experiments" "configs/tls60_s.yaml" --only "${STACK_TLS60_EXPS[@]}"
    run_config "4/4 QUIC60 hybrid block stacking experiments" "configs/quic60_s.yaml" --only "${STACK_QUIC60_EXPS[@]}"
    ;;
  sota40)
    run_config "TLS40/QUIC40 adapted SOTA comparison experiments, seeds 42/2025/3407" "${SOTA_CONFIG}" --only "${SOTA_TLS40_EXPS[@]}" "${SOTA_QUIC40_EXPS[@]}"
    ;;
  sota60)
    run_config "TLS60/QUIC60 adapted SOTA comparison experiments, seeds 42/2025/3407" "${SOTA_CONFIG}" --only "${SOTA_TLS60_EXPS[@]}" "${SOTA_QUIC60_EXPS[@]}"
    ;;
  sota_all)
    run_config "TLS40/QUIC40/TLS60/QUIC60 adapted SOTA comparison experiments, seeds 42/2025/3407" "${SOTA_CONFIG}" --only "${SOTA_ALL_EXPS[@]}"
    ;;
  sota_efficiency)
    run_efficiency "Adapted SOTA FLOPs and inference latency benchmark" --configs "${SOTA_CONFIG}" --output-dir results/efficiency_benchmark --merge-existing --only "${SOTA_ALL_EXPS[@]}" "$@"
    ;;
  efficiency)
    run_efficiency "FLOPs and inference latency benchmark" --output-dir results/efficiency_benchmark "$@"
    ;;
  efficiency_quick)
    run_efficiency "Quick FLOPs and inference latency benchmark" --output-dir results/efficiency_benchmark_quick --batch-sizes 1 32 --repeats 1 --warmup 5 --iterations 20 "$@"
    ;;
  transfer40)
    run_config "TLS<->QUIC 40-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic40_s hybrid_lora_quic_to_tls40_s
    ;;
  transfer60)
    run_config "TLS<->QUIC 60-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic60_s hybrid_lora_quic_to_tls60_s
    ;;
  zero40)
    run_zero_shot "TLS<->QUIC 40-class zero-shot transfer" "${TRANSFER_CONFIG}" --only zero_shot_tls_to_quic40_s zero_shot_quic_to_tls40_s
    ;;
  zero60)
    run_zero_shot "TLS<->QUIC 60-class zero-shot transfer" "${TRANSFER_CONFIG}" --only zero_shot_tls_to_quic60_s zero_shot_quic_to_tls60_s
    ;;
  fullft40)
    run_config "TLS<->QUIC 40-class full fine-tuning transfer" "${TRANSFER_CONFIG}" --only full_ft_tls_to_quic40_s full_ft_quic_to_tls40_s
    ;;
  fullft60)
    run_config "TLS<->QUIC 60-class full fine-tuning transfer" "${TRANSFER_CONFIG}" --only full_ft_tls_to_quic60_s full_ft_quic_to_tls60_s
    ;;
  transfer_extra)
    run_zero_shot "1/4 TLS<->QUIC 40-class zero-shot transfer" "${TRANSFER_CONFIG}" --only zero_shot_tls_to_quic40_s zero_shot_quic_to_tls40_s
    run_config "2/4 TLS<->QUIC 40-class full fine-tuning transfer" "${TRANSFER_CONFIG}" --only full_ft_tls_to_quic40_s full_ft_quic_to_tls40_s
    run_zero_shot "3/4 TLS<->QUIC 60-class zero-shot transfer" "${TRANSFER_CONFIG}" --only zero_shot_tls_to_quic60_s zero_shot_quic_to_tls60_s
    run_config "4/4 TLS<->QUIC 60-class full fine-tuning transfer" "${TRANSFER_CONFIG}" --only full_ft_tls_to_quic60_s full_ft_quic_to_tls60_s
    ;;
  extend_all)
    run_config "1/6 Extend TLS40 experiments" "configs/tls40_s.yaml" --extend
    run_config "2/6 Extend QUIC40 experiments" "configs/quic40_s.yaml" --extend
    run_config "3/6 Extend TLS<->QUIC 40-class LoRA transfer" "${TRANSFER_CONFIG}" --extend --only hybrid_lora_tls_to_quic40_s hybrid_lora_quic_to_tls40_s
    run_config "4/6 Extend TLS60 experiments" "configs/tls60_s.yaml" --extend
    run_config "5/6 Extend QUIC60 experiments" "configs/quic60_s.yaml" --extend
    run_config "6/6 Extend TLS<->QUIC 60-class LoRA transfer" "${TRANSFER_CONFIG}" --extend --only hybrid_lora_tls_to_quic60_s hybrid_lora_quic_to_tls60_s
    ;;
  extend_and_transfer)
    run_config "1/10 Extend TLS40 experiments" "configs/tls40_s.yaml" --extend
    run_config "2/10 Extend QUIC40 experiments" "configs/quic40_s.yaml" --extend
    run_config "3/10 Extend TLS<->QUIC 40-class LoRA transfer" "${TRANSFER_CONFIG}" --extend --only hybrid_lora_tls_to_quic40_s hybrid_lora_quic_to_tls40_s
    run_zero_shot "4/10 TLS<->QUIC 40-class zero-shot transfer" "${TRANSFER_CONFIG}" --only zero_shot_tls_to_quic40_s zero_shot_quic_to_tls40_s
    run_config "5/10 TLS<->QUIC 40-class full fine-tuning transfer" "${TRANSFER_CONFIG}" --only full_ft_tls_to_quic40_s full_ft_quic_to_tls40_s
    run_config "6/10 Extend TLS60 experiments" "configs/tls60_s.yaml" --extend
    run_config "7/10 Extend QUIC60 experiments" "configs/quic60_s.yaml" --extend
    run_config "8/10 Extend TLS<->QUIC 60-class LoRA transfer" "${TRANSFER_CONFIG}" --extend --only hybrid_lora_tls_to_quic60_s hybrid_lora_quic_to_tls60_s
    run_zero_shot "9/10 TLS<->QUIC 60-class zero-shot transfer" "${TRANSFER_CONFIG}" --only zero_shot_tls_to_quic60_s zero_shot_quic_to_tls60_s
    run_config "10/10 TLS<->QUIC 60-class full fine-tuning transfer" "${TRANSFER_CONFIG}" --only full_ft_tls_to_quic60_s full_ft_quic_to_tls60_s
    ;;
  all)
    run_config "1/3 TLS40 experiments" "configs/tls40_s.yaml"
    run_config "2/3 QUIC40 experiments" "configs/quic40_s.yaml"
    run_config "3/3 TLS<->QUIC 40-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic40_s hybrid_lora_quic_to_tls40_s
    ;;
  all60)
    run_config "1/3 TLS60 experiments" "configs/tls60_s.yaml"
    run_config "2/3 QUIC60 experiments" "configs/quic60_s.yaml"
    run_config "3/3 TLS<->QUIC 60-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic60_s hybrid_lora_quic_to_tls60_s
    ;;
  readme_all)
    run_config "1/6 TLS40 experiments" "configs/tls40_s.yaml"
    run_config "2/6 QUIC40 experiments" "configs/quic40_s.yaml"
    run_config "3/6 TLS<->QUIC 40-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic40_s hybrid_lora_quic_to_tls40_s
    run_config "4/6 TLS60 experiments" "configs/tls60_s.yaml"
    run_config "5/6 QUIC60 experiments" "configs/quic60_s.yaml"
    run_config "6/6 TLS<->QUIC 60-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic60_s hybrid_lora_quic_to_tls60_s
    ;;
  quic40_then_all60)
    run_config "1/5 Resume QUIC40 experiments" "configs/quic40_s.yaml"
    run_config "2/5 TLS<->QUIC 40-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic40_s hybrid_lora_quic_to_tls40_s
    run_config "3/5 TLS60 experiments" "configs/tls60_s.yaml"
    run_config "4/5 QUIC60 experiments" "configs/quic60_s.yaml"
    run_config "5/5 TLS<->QUIC 60-class LoRA transfer" "${TRANSFER_CONFIG}" --only hybrid_lora_tls_to_quic60_s hybrid_lora_quic_to_tls60_s
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    echo "Available: all, tls, quic, transfer40, all60, tls60, quic60, ablation40, ablation60, ablation_all, ablation, seed40, seed60, stack40, stack60, stack_all, sota40, sota60, sota_all, sota_efficiency, efficiency, efficiency_quick, transfer60, zero40, zero60, fullft40, fullft60, transfer_extra, extend_all, extend_and_transfer, readme_all, quic40_then_all60"
    exit 1
    ;;
esac

echo
echo "============================================================"
echo "WSL task finished: ${MODE} $(date '+%F %T')"
echo "TLS40 results:  results/tls40_s/all_results.csv"
echo "QUIC40 results: results/quic40_s/all_results.csv"
echo "TLS60 results:  results/tls60_s/all_results.csv"
echo "QUIC60 results: results/quic60_s/all_results.csv"
echo "Transfer results: results/transfer_s/all_results.csv"
echo "SOTA results:     results/sota_adapted/all_results.csv"
echo "Ablation results: results/ablation_s/all_results.csv"
echo "Efficiency results: results/efficiency_benchmark/benchmark_results.csv"
echo "Log: ${LOG}"
echo "============================================================"
echo "OK $(date '+%F %T')" > "${STATUS}"
