"""Tests for the reduced S experiment surface.

The old suite encoded the removed four-task 40/60 matrix. These checks keep
the repository from quietly reintroducing those legacy experiments while
leaving the exact 100-class/open-set configuration to active configs.
"""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"


def _configs() -> list[tuple[Path, dict]]:
    values = []
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as handle:
            values.append((path, yaml.safe_load(handle) or {}))
    return values


def test_only_s_configs_remain():
    paths = [path for path, _ in _configs()]
    assert paths, "at least one experiment configuration is required"
    assert all(
        path.name in {"base.yaml", "compact_s.yaml", "hsta_cm_ablation_s.yaml"}
        for path in paths
    )


def test_configs_do_not_reference_removed_tasks_or_models():
    removed_tokens = (
        "tls40",
        "quic40",
        "tls60",
        "quic60",
        "gru",
        "transformer",
    )
    for path, _ in _configs():
        text = path.read_text(encoding="utf-8").lower()
        for token in removed_tokens:
            assert token not in text, f"{path.name} still references removed {token}"


def test_compact_matrix_contains_only_primary_comparisons():
    path = CONFIG_DIR / "compact_s.yaml"
    if not path.exists():
        return
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    names = {str(exp.get("model", "")).lower() for exp in cfg.get("experiments", [])}
    assert names <= {
        "hsta",
        "30pkttcnet-adapted",
        "netmamba-adapted",
        "30pkttcnet_adapted",
        "netmamba_adapted",
        "srvit",
        "trafficaudio",
        "bpf-gnn",
        "bpf_gnn",
    }
    assert {"hsta", "srvit", "trafficaudio", "bpf-gnn"} <= names
    model_cfg = cfg.get("base", {}).get("model_cfg", {})
    assert model_cfg.get("attention_backend") == "flash"


def test_runner_does_not_expose_removed_modes():
    runner = (ROOT / "scripts" / "run_wsl_experiments.sh").read_text(encoding="utf-8").lower()
    for token in (
        "tls40",
        "quic40",
        "tls60",
        "quic60",
        "recent_all",
        "sota_all",
        "evidence",
    ):
        assert token not in runner
