"""Tests for the reduced S experiment surface.

The old suite encoded the removed four-task 40/60 matrix. These checks keep
the repository from quietly reintroducing those legacy experiments while
leaving the exact 100-class/open-set configuration to active configs.
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from models import build_model


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
        path.name in {"compact_s.yaml", "hsta_cm_ablation_s.yaml"}
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


def test_compact_matrix_contains_dft_primary_model_and_no_dft_ablation():
    path = CONFIG_DIR / "compact_s.yaml"
    if not path.exists():
        return
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    names = {str(exp.get("model", "")).lower() for exp in cfg.get("experiments", [])}
    assert names <= {
        "hsta-cm",
        "hsta-cm-dft",
        "30pkttcnet-adapted",
        "netmamba-adapted",
        "30pkttcnet_adapted",
        "netmamba_adapted",
        "srvit",
        "trafficaudio",
        "bpf-gnn",
        "bpf_gnn",
    }
    assert names == {
        "hsta-cm",
        "hsta-cm-dft",
        "30pkttcnet-adapted",
        "netmamba-adapted",
        "srvit",
        "trafficaudio",
        "bpf-gnn",
    }
    assert {"hsta-cm", "srvit", "trafficaudio", "bpf-gnn"} <= names
    dft_experiments = [
        exp for exp in cfg.get("experiments", [])
        if str(exp.get("model", "")).lower() == "hsta-cm-dft"
    ]
    assert {exp["exp_name"] for exp in dft_experiments} == {
        "hsta_cm_dft_tls22_s_seed599",
        "hsta_cm_dft_tls22_s_seed5009",
        "hsta_cm_dft_tls22_s_seed813",
        "hsta_cm_dft_closed_tls22_s_seed599",
        "hsta_cm_dft_quic22_s_seed599",
        "hsta_cm_dft_quic22_s_seed5009",
        "hsta_cm_dft_quic22_s_seed813",
        "hsta_cm_dft_closed_quic22_s_seed599",
    }
    assert {int(exp["seed"]) for exp in dft_experiments} == {599, 5009, 813}
    hsta_experiments = [
        exp for exp in cfg.get("experiments", [])
        if str(exp.get("model", "")).lower() == "hsta-cm"
    ]
    assert {int(exp["seed"]) for exp in hsta_experiments} == {599}
    by_name = {str(exp["exp_name"]): exp for exp in cfg.get("experiments", [])}
    for exp_name in ("tcnet_tls22_s", "tcnet_quic22_s"):
        assert by_name[exp_name]["model_cfg"]["depth"] == 5
    for exp_name in ("netmamba_tls22_s", "netmamba_quic22_s"):
        assert by_name[exp_name]["model_cfg"]["depth"] == 5
        assert by_name[exp_name]["model_cfg"]["max_len"] == 256
    for exp_name in ("srvit_tls22_s", "srvit_quic22_s"):
        assert by_name[exp_name]["model_cfg"]["depth"] == 4
    for exp_name in ("trafficaudio_tls22_s", "trafficaudio_quic22_s"):
        audio_cfg = by_name[exp_name]["model_cfg"]
        assert audio_cfg["n_fft"] == 32
        assert audio_cfg["n_mels"] <= audio_cfg["n_fft"] // 2 + 1
    model_cfg = cfg.get("base", {}).get("model_cfg", {})
    assert model_cfg.get("attention_backend") == "flash"
    by_name = {str(exp["exp_name"]): exp for exp in cfg.get("experiments", [])}
    assert all(by_name[name].get("train_unknown", True) for name in (
        "hsta_cm_dft_tls22_s_seed599", "hsta_cm_dft_tls22_s_seed5009",
        "hsta_cm_dft_tls22_s_seed813", "hsta_cm_no_dft_tls22_s_seed599",
        "hsta_cm_dft_quic22_s_seed599", "hsta_cm_dft_quic22_s_seed5009",
        "hsta_cm_dft_quic22_s_seed813", "hsta_cm_no_dft_quic22_s_seed599",
    ))
    assert all(not by_name[name].get("train_unknown", True) for name in (
        "hsta_cm_dft_closed_tls22_s_seed599",
        "hsta_cm_dft_closed_quic22_s_seed599",
    ))
    assert all(not by_name[name].get("train_unknown", True) for name in (
        "tcnet_tls22_s", "netmamba_tls22_s", "srvit_tls22_s",
        "trafficaudio_tls22_s", "bpfgnn_tls22_s", "tcnet_quic22_s",
        "netmamba_quic22_s", "srvit_quic22_s", "trafficaudio_quic22_s",
        "bpfgnn_quic22_s",
    ))


def test_hsta_cm_ablation_matrix_is_four_by_two():
    cfg = yaml.safe_load((CONFIG_DIR / "hsta_cm_ablation_s.yaml").read_text(encoding="utf-8"))
    names = {str(exp["exp_name"]) for exp in cfg["experiments"]}
    assert len(names) == 8
    assert {"full", "no_conv", "no_mamba", "no_attention"} <= {
        name.split("hsta_cm_", 1)[1].rsplit("_", 2)[0] for name in names
    }


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


def test_legacy_hsta_registry_name_is_removed():
    with pytest.raises(ValueError):
        build_model("hsta", input_dim=3, num_classes=101, seq_len=30, cfg={})
