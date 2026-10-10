"""Regression checks for the canonical 60-class small experiment scope."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from models import build_model


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"


def _load(name: str) -> dict:
    path = CONFIG_DIR / name
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def test_only_current_configs_remain():
    names = {path.name for path in CONFIG_DIR.glob("*.yaml")}
    assert names == {
        "compact_s.yaml",
        "hsta_cm_ablation_s.yaml",
        "hsta_cm_large_variants.yaml",
    }


def test_compact_matrix_is_60_class_small_seed599():
    cfg = _load("compact_s.yaml")
    base = cfg["base"]
    experiments = cfg["experiments"]
    assert len(experiments) == 14
    assert base["seed"] == 599
    assert base["epochs"] == 100
    assert base["patience"] == 15
    assert base["seq_len"] == 30
    assert base["early_stop_metric"] == "val_known_macro_f1"
    assert base["lr_scheduler_metric"] == "val_known_macro_f1"
    assert base["model_cfg"]["dim"] == 256
    assert base["model_cfg"]["attention_backend"] == "flash"

    names = {str(exp["exp_name"]) for exp in experiments}
    assert len({name for name in names if "tls60" in name}) == 7
    assert len({name for name in names if "quic60" in name}) == 7
    assert all(int(exp["seed"]) == 599 for exp in experiments)
    assert all("datazoo_tls60_s_protocol_small_sampled.csv" in exp["data_csv"] or
               "datazoo_quic60_s_protocol_small_sampled.csv" in exp["data_csv"]
               for exp in experiments)
    models = {str(exp["model"]).lower() for exp in experiments}
    assert models == {
        "hsta-cm", "30pkttcnet-adapted", "netmamba-adapted", "srvit",
        "trafficaudio", "bpf-gnn",
    }
    open_runs = [exp for exp in experiments if "_open_" in exp["exp_name"]]
    closed_runs = [exp for exp in experiments if "_closed_" in exp["exp_name"]]
    assert len(open_runs) == 2
    assert all(exp.get("train_unknown") is True for exp in open_runs)
    assert len(closed_runs) == 2
    assert all(exp.get("train_unknown") is False for exp in closed_runs)
    assert all(exp.get("train_unknown") is False for exp in experiments
               if exp not in open_runs)


def test_ablation_matrix_is_three_by_two_open_set():
    cfg = _load("hsta_cm_ablation_s.yaml")
    base = cfg["base"]
    experiments = cfg["experiments"]
    assert len(experiments) == 6
    assert base["model"] == "hsta-cm"
    assert base["seed"] == 599
    assert base["epochs"] == 100
    assert base["patience"] == 15
    assert base["early_stop_metric"] == "val_known_macro_f1"
    assert base["lr_scheduler_metric"] == "val_known_macro_f1"
    assert base["model_cfg"]["dim"] == 256
    assert base["model_cfg"]["use_conv"] is True
    assert base["model_cfg"]["use_mamba"] is True
    assert base["model_cfg"]["use_attention"] is True
    assert all(exp.get("seed") == 599 for exp in experiments)
    assert all(exp.get("train_unknown") is True for exp in experiments)
    assert {name.split("_open_", 1)[0] for name in
            (exp["exp_name"] for exp in experiments)} == {
                "hsta_cm_no_conv", "hsta_cm_no_mamba", "hsta_cm_no_attention",
            }
    assert all("60_s_protocol_small_sampled.csv" in exp["data_csv"] for exp in experiments)


def test_large_variant_matrix_has_three_candidates_per_dataset():
    cfg = _load("hsta_cm_large_variants.yaml")
    base = cfg["base"]
    experiments = cfg["experiments"]
    assert len(experiments) == 6
    assert base["seed"] == 599
    assert base["epochs"] == 100
    assert base["patience"] == 15
    assert base["batch_size"] == 4096
    assert base["model_cfg"]["dim"] == 256
    assert base["model_cfg"]["use_packet_position"] is True
    assert base["model_cfg"]["use_branch_type"] is True
    assert all("protocol_large_sampled.csv" in exp["data_csv"] for exp in experiments)
    assert all(exp["train_unknown"] is True for exp in experiments)
    prefixes = {"hsta_cm_multiscale", "hsta_cm_dual_plus_dft", "hsta_cm_tri_multiscale_dft"}
    assert {exp["exp_name"].rsplit("_tls60_s_large_seed599", 1)[0]
            for exp in experiments if "tls60" in exp["exp_name"]} == prefixes
    assert {exp["exp_name"].rsplit("_quic60_s_large_seed599", 1)[0]
            for exp in experiments if "quic60" in exp["exp_name"]} == prefixes


def test_legacy_hsta_registry_name_is_removed():
    with pytest.raises(ValueError):
        build_model("hsta", input_dim=3, num_classes=61, seq_len=30, cfg={})
