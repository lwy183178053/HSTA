import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASKS = ("tls40_s", "quic40_s", "tls60_s", "quic60_s")
SEEDS = (42, 2025, 3407)


def load_config(name):
    with (ROOT / "configs" / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class FinalExperimentConfigTests(unittest.TestCase):
    def test_main_configs_cover_gru_and_transformer(self):
        for task in TASKS:
            cfg = load_config(f"{task}.yaml")
            observed = {
                (exp["model"], int(exp.get("seed", cfg["base"]["seed"])))
                for exp in cfg["experiments"]
            }
            expected = {("gru", seed) for seed in SEEDS} | {
                ("transformer", seed) for seed in SEEDS
            }
            self.assertEqual(observed, expected)

    def test_recent_baselines_cover_three_models_four_tasks_three_seeds(self):
        cfg = load_config("recent_journal_baselines.yaml")
        self.assertEqual(len(cfg["experiments"]), 36)
        observed = {
            (exp["model"], task, int(exp.get("seed", cfg["base"]["seed"])))
            for exp in cfg["experiments"]
            for task in TASKS
            if task in exp["exp_name"]
        }
        expected = {
            (model, task, seed)
            for model in ("srvit", "trafficaudio", "bpf_gnn")
            for task in TASKS
            for seed in SEEDS
        }
        self.assertEqual(observed, expected)

    def test_hsta_flash_main_and_ablation_layouts(self):
        main = load_config("hsta_flash.yaml")
        self.assertEqual(len(main["experiments"]), 12)
        self.assertEqual(main["base"]["model_cfg"]["attention_backend"], "flash")
        self.assertEqual(
            main["base"]["model_cfg"]["layout"],
            ["mamba", "mamba", "mlp", "attention", "mlp"],
        )

        ablation = load_config("hsta_flash_ablation.yaml")
        self.assertEqual(len(ablation["experiments"]), 24)
        self.assertTrue(
            all(
                "attention_front" in exp["exp_name"]
                or "attention_middle" in exp["exp_name"]
                for exp in ablation["experiments"]
            )
        )

        no_attention = load_config("hsta_no_attention.yaml")
        self.assertEqual(len(no_attention["experiments"]), 12)
        self.assertEqual(
            no_attention["base"]["model_cfg"]["layout"],
            ["mamba", "mamba", "mlp", "mlp", "mlp"],
        )

    def test_model_package_matches_final_scope(self):
        model_files = {path.name for path in (ROOT / "models").glob("*.py")}
        self.assertEqual(
            model_files,
            {
                "__init__.py",
                "adapted_sota.py",
                "gru.py",
                "hsta.py",
                "mamba_model.py",
                "recent_journal_baselines.py",
                "transformer.py",
            },
        )

        runner = (ROOT / "scripts" / "run_wsl_experiments.sh").read_text(encoding="utf-8")
        for mode in ("main_all", "recent_all", "sota_all", "ablation_all", "hsta_flash_all", "efficiency"):
            self.assertIn(mode, runner)


if __name__ == "__main__":
    unittest.main()
