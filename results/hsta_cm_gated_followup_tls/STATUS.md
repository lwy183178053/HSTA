# HSTA-CM Gated Follow-up Status

This snapshot records the TLS seed-599 follow-up experiments.

Completed runs with final `summary.csv` and `metrics.json`:

- `bounded_scale_tls60_seed599`
- `bounded_no_mamba_outer_tls60_seed599`
- `bounded_no_dft_tls60_seed599`
- `bounded_nonlocal_gnn_tls60_seed599`

`bounded_time_cnn_tls60_seed599` is a partial snapshot. Its checkpoint and
history were saved while training was interrupted; it has no final
`summary.csv` or `metrics.json` and must not be treated as a completed
comparison.

Checkpoint files and runtime logs remain local and are intentionally excluded
from Git.
