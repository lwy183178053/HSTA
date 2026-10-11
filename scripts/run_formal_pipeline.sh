#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
mkdir -p logs data/processed
# Keep the full traceback from export/training stages in one place.  The
# caller may redirect this script to the background, so stdout alone is not
# sufficient for diagnosing a failed long-running stage.
exec > >(tee -a logs/formal_pipeline.log) 2>&1
exec 9>logs/formal_pipeline.lock
flock -n 9 || { echo "正式队列已在运行" >&2; exit 1; }
status=logs/formal_pipeline.status
stage=starting
update() { stage="$1"; printf "%s %s\n" "$(date -u +%FT%TZ)" "$stage" > "$status"; }
failed() {
  local code=$?
  printf "%s failed:%s exit:%s command:%s\n" "$(date -u +%FT%TZ)" "$stage" "$code" "$BASH_COMMAND" | tee "$status" >&2
  exit "$code"
}
trap failed ERR
update acceptance
python -m pytest -q
python scripts/smoke_cuda.py
update export
if [[ "${DATA_EXPORT_RUNTIME:-windows}" == "windows" ]]; then
  # H5 and CSV work is substantially faster in the native Windows process
  # than through WSL's /mnt/e bridge. Training remains in this WSL script.
  windows_root="$(wslpath -w "$ROOT")"
  powershell.exe -NoProfile -ExecutionPolicy Bypass \
    -File "$(wslpath -w "$ROOT/scripts/export_formal_windows.ps1")" \
    -ProjectRoot "$windows_root" \
    -DatazooWorkers "${DATAZOO_WORKERS:-auto}" \
    -DatazooBatchSize "${DATAZOO_BATCH_SIZE:-2048}" \
    -DatazooTestBatchSize "${DATAZOO_TEST_BATCH_SIZE:-2048}" \
    -TopK 60 -MaxTrainPerClass 10000 -MaxValPerClass 2000 -MaxTestPerClass 2000 \
    -NoiseRatio 0.10 -UnknownRatio 0.30
else
  for dataset in tls quic; do
    update "export_${dataset}"
    python -m data.preprocess --dataset "$dataset" --size S --topk 60 \
      --max-train-per-class 10000 --max-val-per-class 2000 --max-test-per-class 2000 \
      --noise-ratio 0.10 --datazoo-workers "${DATAZOO_WORKERS:-auto}" \
      --datazoo-batch-size "${DATAZOO_BATCH_SIZE:-2048}" \
      --datazoo-test-batch-size "${DATAZOO_TEST_BATCH_SIZE:-2048}" \
      --out-csv "data/processed/datazoo_${dataset}60_s_protocol.csv"
    update "audit_${dataset}"
    python scripts/audit_open_set_dataset.py --input-csv "data/processed/datazoo_${dataset}60_s_protocol.csv" --expected-known 60
  done
fi
update main
bash scripts/run_wsl_experiments.sh main
update ablation
bash scripts/run_wsl_experiments.sh ablation
update efficiency
bash scripts/run_wsl_experiments.sh efficiency
update summary
python scripts/summarize_compact_results.py
update completed
touch logs/formal_pipeline.completed
