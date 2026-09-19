#!/usr/bin/env bash
# =============================================================================
# HSTA v13 evidence pack
# -----------------------------------------------------------------------------
# Rebuilds the missing/weak evidence behind the JNCA submission:
#
#   stage_ablation   Re-runs the "No Attention" ablation that Table 4 reports but
#                    for which NO run record exists on disk. 12 runs
#                    (4 tasks x 3 seeds) on the flash backend.
#
#   stage_alignment  Runs the parameter-matched Transformer/Mamba baselines that
#                    neutralise the "41.5% fewer parameters" objection (24 runs).
#
#   stage_all        Both, sequentially. For parallel execution use
#                    `parallel_ablation` / `parallel_alignment`.
#
#   report           Regenerates every table from raw run records and runs the
#                    significance tests. No training.
#
#   probe            Prints the measured parameter count of each candidate model
#                    so the matched depths can be chosen from real numbers.
#
# USAGE (from the repository root, inside WSL)
#   bash scripts/run_evidence_pack.sh probe
#   bash scripts/run_evidence_pack.sh stage_ablation
#   bash scripts/run_evidence_pack.sh parallel_ablation 3
#   bash scripts/run_evidence_pack.sh stage_alignment
#   bash scripts/run_evidence_pack.sh report
#
# Every stage is RESUME-SAFE: run_experiments.py --resume skips any experiment
# whose summary.csv and best.pt already exist, so re-running is cheap.
#
# RUNTIME (single RTX 5070, ~20-35 min per run at batch 512 / <=100 epochs)
#   stage_ablation    12 runs   ~4-7 h serial,  ~1.5-2.5 h with 3 workers
#   stage_alignment   24 runs   ~7-13 h serial
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

MODE="${1:-report}"
if [ "$#" -gt 0 ]; then shift; fi

LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
STAMP="$(date '+%Y%m%d_%H%M%S')"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
activate_env() {
  if [ -f /opt/traffic-mamba-venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source /opt/traffic-mamba-venv/bin/activate
  else
    echo "[warn] /opt/traffic-mamba-venv not found; using the current interpreter."
    echo "[warn] Mamba requires CUDA on Linux; results will not be comparable otherwise."
  fi
  export PYTHONUNBUFFERED=1
  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
  export MKL_NUM_THREADS="${MKL_NUM_THREADS:-4}"
  export NUMEXPR_MAX_THREADS="${NUMEXPR_MAX_THREADS:-4}"
}

# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------
run_ablation() {
  echo "===== No Attention ablation (rebuilt) ====="
  python run_experiments.py --config configs/hsta_no_attention_v13.yaml --resume
}

run_alignment() {
  if [ ! -f configs/alignment_baselines_v13.yaml ]; then
    echo "[error] configs/alignment_baselines_v13.yaml is missing."
    echo "        Run the probe first:  bash scripts/run_evidence_pack.sh probe"
    exit 1
  fi
  echo "===== Parameter-matched baselines ====="
  python run_experiments.py --config configs/alignment_baselines_v13.yaml --resume
}

run_probe() {
  echo "===== Parameter-count probe ====="
  python scripts/alignment_models.py
}

run_report() {
  echo "===== Evidence report ====="
  python scripts/aggregate_evidence.py --results results --out results/evidence_report
}

run_calc() {
  echo "===== Ratio / parameter-budget calculator (no GPU) ====="
  python scripts/ratio_calculator.py
}

run_ratio() {
  echo "===== Mamba:Attention ratio study ====="
  python run_experiments.py --config configs/ratio_scale_v13.yaml --resume
}

run_ratio_report() {
  echo "===== Ratio + placement analysis ====="
  python scripts/ratio_analysis.py --results results --out results/ratio_report
}

run_placement() {
  echo "===== Attention placement, extended seeds ====="
  echo "Reusing results/hsta_flash_ablation so existing seeds are not re-trained."
  python run_experiments.py --config configs/placement_v13.yaml --resume \
    --output-dir results/hsta_flash_ablation
}

# Fan a list of experiment names out across N workers.
#
# Isolation strategy: every worker writes to a PRIVATE scratch root, then the
# run directories are consolidated into the real output dir once all workers
# have finished.
#
# Why not just run all workers into the real output dir: run_experiments.py
# runs with --resume, and _completed_result() skips an experiment as soon as
# summary.csv and best.pt exist. Two workers sharing one output dir could
# therefore observe a half-written run from another worker and skip real work.
# The scratch root lives under logs/ (NOT under results/) so that
# scripts/aggregate_evidence.py cannot discover duplicate copies of a run.
parallel_stage() {
  local config="$1" workers="$2" tag="$3"
  local final_dir="${4:-}"

  local real_out scratch
  if [ -n "${final_dir}" ]; then
    real_out="${final_dir}"
  else
    real_out="$(python - "$config" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as fh:
    print(yaml.safe_load(fh)["base"]["output_dir"])
PY
)"
  fi
  scratch="${PROJECT_ROOT}/logs/_scratch_${tag}_${STAMP:-run}"
  mkdir -p "${scratch}"
  # Guard against a trailing slash turning "${real_out}/" into "results//"
  real_out="${real_out%/}"

  local names
  names="$(python - "$config" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as fh:
    cfg = yaml.safe_load(fh)
for exp in cfg["experiments"]:
    print(exp["exp_name"])
PY
)"
  local total
  total="$(echo "${names}" | wc -l)"
  echo "Fanning out ${total} experiments across ${workers} workers."
  echo "  scratch : ${scratch}"
  echo "  final   : ${real_out}"

  local i=0
  for name in ${names}; do
    local slot=$(( i % workers ))
    echo "  -> ${name} (worker ${slot})"
    (
      python run_experiments.py --config "${config}" --resume --only "${name}" \
        --output-dir "${scratch}/${name}" \
        > "${LOG_DIR}/v13_${tag}_${name}.log" 2>&1
      echo "    done ${name}"
    ) &
    i=$(( i + 1 ))
    if [ $(( i % workers )) -eq 0 ]; then
      wait
    fi
  done
  wait

  # Consolidate the run directories into the real output root.
  #
  # --output-dir redirects the AGGREGATED CSV to the scratch root, but each
  # run's own artefacts still land at <scratch>/<exp_name>/. A plain
  # `cp -r <scratch>/* <real_out>/` therefore nests them one level too deep:
  #   results/<study>/<exp_name>/<exp_name>/metrics.json
  # which the aggregator cannot find. Flatten explicitly and VERIFY.
  mkdir -p "${real_out}"
  local copied=0 missing=0
  for run_dir in "${scratch}"/*; do
    [ -d "${run_dir}" ] || continue
    local base
    base="$(basename "${run_dir}")"

    if [ -f "${run_dir}/${base}/metrics.json" ]; then
      # Nested layout: pull the inner artefacts up one level.
      cp -rf "${run_dir}/${base}/." "${real_out}/${base}/"
    elif [ -f "${run_dir}/metrics.json" ]; then
      # Already flat.
      mkdir -p "${real_out}/${base}"
      cp -rf "${run_dir}/." "${real_out}/${base}/"
    else
      echo "  [warn] ${base}: no metrics.json found to consolidate (run may have failed)"
      missing=$(( missing + 1 ))
      continue
    fi

    if [ -f "${real_out}/${base}/metrics.json" ]; then
      copied=$(( copied + 1 ))
    else
      echo "  [warn] ${base}: consolidation produced no metrics.json"
      missing=$(( missing + 1 ))
    fi
  done
  rm -rf "${scratch}"
  echo "Consolidated ${copied} run directories into ${real_out} (${missing} problem(s))"
  if [ "${missing}" -gt 0 ]; then
    echo "  [warn] ${missing} run(s) did not consolidate. Check the per-run logs in ${LOG_DIR}."
  fi
  echo "All ${tag} runs finished."
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
case "${MODE}" in
  probe)
    activate_env
    run_probe
    ;;
  stage_ablation)
    activate_env
    exec > >(tee -a "${LOG_DIR}/v13_ablation_${STAMP}.log") 2>&1
    run_ablation
    ;;
  stage_alignment)
    activate_env
    exec > >(tee -a "${LOG_DIR}/v13_alignment_${STAMP}.log") 2>&1
    run_alignment
    ;;
  stage_all)
    activate_env
    exec > >(tee -a "${LOG_DIR}/v13_all_${STAMP}.log") 2>&1
    run_ablation
    run_alignment
    run_report
    ;;
  parallel_ablation)
    activate_env
    parallel_stage configs/hsta_no_attention_v13.yaml "${1:-3}" ablation
    run_report
    ;;
  parallel_alignment)
    activate_env
    parallel_stage configs/alignment_baselines_v13.yaml "${1:-3}" alignment
    run_report
    ;;
  calc)
    activate_env
    run_calc
    ;;
  stage_ratio)
    activate_env
    exec > >(tee -a "${LOG_DIR}/v13_ratio_${STAMP}.log") 2>&1
    run_ratio
    run_ratio_report
    ;;
  parallel_ratio)
    activate_env
    parallel_stage configs/ratio_scale_v13.yaml "${1:-3}" ratio
    run_ratio_report
    ;;
  stage_ratio_budget)
    activate_env
    exec > >(tee -a "${LOG_DIR}/v13_ratiobud_${STAMP}.log") 2>&1
    python run_experiments.py --config configs/ratio_budget_v13.yaml --resume
    run_ratio_report
    ;;
  parallel_ratio_budget)
    activate_env
    parallel_stage configs/ratio_budget_v13.yaml "${1:-3}" ratiobud
    run_ratio_report
    ;;
  stage_placement)
    activate_env
    exec > >(tee -a "${LOG_DIR}/v13_placement_${STAMP}.log") 2>&1
    run_placement
    run_ratio_report
    ;;
  parallel_placement)
    activate_env
    parallel_stage configs/placement_v13.yaml "${1:-3}" placement results/hsta_flash_ablation
    run_ratio_report
    ;;
  ratio_report)
    activate_env
    run_ratio_report
    ;;
  report)
    activate_env
    run_report
    ;;
  *)
    cat <<EOF
Unknown mode: ${MODE}

Available:
  calc                        ratio / parameter-budget calculator -- NO GPU, seconds
  probe                       measured parameter counts for every candidate model
  stage_ratio                 run the fixed-WIDTH ratio study, then report
  parallel_ratio [N]          same as stage_ratio but N workers in parallel (default 3)
  stage_ratio_budget          run the PARAMETER-MATCHED ratio study (Study 2)
  parallel_ratio_budget [N]   same, parallel -- this is the one that can attribute
                              a difference to the RATIO rather than to model size
  stage_placement             add the 3 missing seeds to the placement ablation
  parallel_placement [N]      same, parallel; reuses results/hsta_flash_ablation
  ratio_report                ratio + placement analysis, no training
  stage_ablation              re-run the legacy No Attention ablation (12 runs)
  stage_alignment             run parameter-matched baselines (24 runs, QUIC-60)
  stage_all                   ablation + alignment + report, sequentially
  parallel_ablation [N]       same as stage_ablation but N workers in parallel
  parallel_alignment [N]      same as stage_alignment but N workers in parallel
  report                      regenerate tables + significance tests, no training
EOF
    exit 1
    ;;
esac

echo
echo "Finished: ${MODE} $(date '+%F %T')"
