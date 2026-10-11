#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
mkdir -p logs data/processed
exec 9>logs/formal_pipeline.lock
flock -n 9 || { echo "正式队列已在运行" >&2; exit 1; }
status=logs/formal_pipeline.status
stage=starting
update() { stage="$1"; printf "%s %s\n" "$(date -u +%FT%TZ)" "$stage" > "$status"; }
failed() { local code=$?; printf "%s failed:%s exit:%s\n" "$(date -u +%FT%TZ)" "$stage" "$code" > "$status"; exit "$code"; }
trap failed ERR
update acceptance
python -m pytest -q
python scripts/smoke_cuda.py
for dataset in tls quic; do
  update "export_${dataset}"
  python -m data.preprocess --dataset "$dataset" --size S --topk 60 \
    --max-train-per-class 10000 --max-val-per-class 2000 --max-test-per-class 2000 \
    --noise-ratio 0.10 --out-csv "data/processed/datazoo_${dataset}60_s_protocol.csv"
  update "audit_${dataset}"
  python scripts/audit_open_set_dataset.py --input-csv "data/processed/datazoo_${dataset}60_s_protocol.csv" --expected-known 60
done
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
