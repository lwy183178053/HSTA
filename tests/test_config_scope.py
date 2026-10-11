"""正式 60 类实验配置的完整性检查。"""
from pathlib import Path
import yaml
from experiment_config import expand_seeded_experiments

ROOT = Path(__file__).resolve().parents[1]

def test_formal_matrix_and_single_dataset_per_protocol():
    assert {p.name for p in (ROOT / "configs").glob("*.yaml")} == {"compact_s.yaml", "hsta_cm_ablation_s.yaml"}
    for name, expected in [("compact_s.yaml", 42), ("hsta_cm_ablation_s.yaml", 18)]:
        cfg = yaml.safe_load((ROOT / "configs" / name).read_text(encoding="utf-8"))
        assert cfg["seeds"] == [599, 5009, 813]
        runs = expand_seeded_experiments(cfg)
        assert len(runs) == expected
        assert len({r["exp_name"] for r in runs}) == expected
        assert {r["data_csv"] for r in runs} == {f"data/processed/datazoo_{ds}60_s_protocol.csv" for ds in ("tls", "quic")}
        base = cfg["base"]
        assert (base["epochs"], base["patience"], base["seq_len"]) == (100, 15, 30)
        assert (base["batch_size"], base["eval_batch_size"]) == (4096, 512)
        assert base["oom_microbatch_fallbacks"] == [2048, 1024, 512]
        assert base["early_stop_metric"] == base["lr_scheduler_metric"] == "val_known_macro_f1"
        assert base["model_cfg"]["dim"] == 256
        assert base["output_dir"] == (
            "results/formal60" if name == "compact_s.yaml"
            else "results/hsta_cm_ablation_formal60"
        )
        assert all(not r["exp_name"].endswith("_s") for r in runs)
        if name == "compact_s.yaml":
            assert sum(r["train_unknown"] for r in runs) == 6
            assert {r["model"] for r in runs} == {"hsta-cm", "30pkttcnet-adapted", "netmamba-adapted", "srvit", "trafficaudio", "bpf-gnn"}
        else:
            assert all(r["train_unknown"] for r in runs)
            assert all(len(r["model_cfg"]) == 1 for r in runs)
