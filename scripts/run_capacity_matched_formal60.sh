#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source /opt/traffic-mamba-venv/bin/activate
export PYTHONUNBUFFERED=1
mkdir -p logs
exec > >(tee -a logs/capacity_matched_formal60.log) 2>&1
exec 9>logs/capacity_matched_formal60.lock
flock -n 9 || { echo "容量匹配实验队列已在运行" >&2; exit 1; }
status=logs/capacity_matched_formal60.status
completed=logs/capacity_matched_formal60.completed
printf '%s %s\n' "$(date -u +%FT%TZ)" "starting" > "$status"
rm -f "$completed"
failed() {
  local code=$?
  printf '%s failed:%s exit:%s command:%s\n' "$(date -u +%FT%TZ)" "$stage" "$code" "$BASH_COMMAND" > "$status"
  exit "$code"
}
trap failed ERR
stage=main
printf '%s %s\n' "$(date -u +%FT%TZ)" "$stage" > "$status"
bash scripts/run_wsl_experiments.sh main
stage=ablation
printf '%s %s\n' "$(date -u +%FT%TZ)" "$stage" > "$status"
bash scripts/run_wsl_experiments.sh ablation
stage=efficiency
printf '%s %s\n' "$(date -u +%FT%TZ)" "$stage" > "$status"
bash scripts/run_wsl_experiments.sh efficiency
stage=summary
printf '%s %s\n' "$(date -u +%FT%TZ)" "$stage" > "$status"
python scripts/summarize_compact_results.py
printf '%s completed\n' "$(date -u +%FT%TZ)" > "$status"
touch "$completed"
