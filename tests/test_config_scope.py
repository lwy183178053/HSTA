"""Formal MVIF-Net and baseline configuration checks."""

from pathlib import Path

import yaml

from experiment_config import expand_seeded_experiments
from scripts.summarize_compact_results import _expected_experiments


ROOT = Path(__file__).resolve().parents[1]


def test_formal_matrix_has_open_closed_mvif_and_five_baselines():
    cfg = yaml.safe_load((ROOT / "configs" / "compact_s.yaml").read_text(encoding="utf-8"))
    runs = expand_seeded_experiments(cfg)
    assert _expected_experiments() == {run["exp_name"] for run in runs}

    assert cfg["seeds"] == [599, 5009, 813]
    assert len(runs) == 42
    assert len({run["exp_name"] for run in runs}) == 42
    assert {run["data_csv"] for run in runs} == {
        f"data/processed/datazoo_{dataset}60_s_protocol.csv" for dataset in ("tls", "quic")
    }
    assert {run["model"] for run in runs} == {
        "mvif-net",
        "30pkttcnet-adapted",
        "netmamba-adapted",
        "srvit",
        "trafficaudio",
        "bpf-gnn",
    }
    assert sum(bool(run["train_unknown"]) for run in runs) == 6

    base = cfg["base"]
    assert (base["epochs"], base["patience"], base["seq_len"]) == (100, 15, 30)
    assert (base["batch_size"], base["eval_batch_size"]) == (4096, 512)
    assert base["oom_microbatch_fallbacks"] == [2048, 1024, 512]
    assert base["early_stop_metric"] == base["lr_scheduler_metric"] == "val_known_macro_f1"
    assert base["model_cfg"]["dim"] == 256
    assert base["output_dir"] == "results/mvif_net_masked_global_pooling"

    mvif_runs = [run for run in runs if run["model"] == "mvif-net"]
    assert {run["exp_name"] for run in mvif_runs} == {
        "mvif_net_open_tls60_seed599",
        "mvif_net_open_tls60_seed5009",
        "mvif_net_open_tls60_seed813",
        "mvif_net_open_quic60_seed599",
        "mvif_net_open_quic60_seed5009",
        "mvif_net_open_quic60_seed813",
        "mvif_net_closed_tls60_seed599",
        "mvif_net_closed_tls60_seed5009",
        "mvif_net_closed_tls60_seed813",
        "mvif_net_closed_quic60_seed599",
        "mvif_net_closed_quic60_seed5009",
        "mvif_net_closed_quic60_seed813",
    }
    assert sum(bool(run["train_unknown"]) for run in mvif_runs) == 6
    assert sum(not bool(run["train_unknown"]) for run in mvif_runs) == 6
    assert {run["data_csv"] for run in mvif_runs} == {
        "data/processed/datazoo_tls60_s_protocol.csv",
        "data/processed/datazoo_quic60_s_protocol.csv",
    }
    assert all(run["model_cfg"]["graph_k"] == 4 for run in mvif_runs)
    assert all(run["model_cfg"]["branch_residual_init"] == 0.1 for run in mvif_runs)
    assert all(run["model_cfg"]["residual_scale_max"] == 0.5 for run in mvif_runs)

    baseline_runs = [run for run in runs if run["model"] != "mvif-net"]
    assert len(baseline_runs) == 30
    assert all(not run["train_unknown"] for run in baseline_runs)
    assert {run["output_dir"] for run in baseline_runs} == {"results/formal60"}


def test_bimamba_plus_probe_isolated_to_one_seed():
    cfg_path = ROOT / "configs" / "mvif_bimamba_plus_seed599.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    runs = expand_seeded_experiments(cfg)

    assert cfg["seeds"] == [599]
    assert len(runs) == 4
    assert {run["model"] for run in runs} == {"mvif-bimamba-plus"}
    assert {run["seed"] for run in runs} == {599}
    assert cfg["base"]["output_dir"] == "results/mvif_bimamba_plus_seed599"
    assert cfg["base"]["batch_size"] == 4096
    assert cfg["base"]["train_microbatch_size"] == 512
    assert {run["train_unknown"] for run in runs} == {True, False}
