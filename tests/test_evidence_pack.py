"""Tests for the v13 evidence pack.

These pin down the fixes made while rebuilding the missing ablation and adding
the parameter-matched baselines, so the corrections cannot silently regress.

Run:
    cd E:\\AllProject\\流量分析python项目\\HSTA
    & 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' -m unittest tests.test_evidence_pack -v
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = ("tls40_s", "quic40_s", "tls60_s", "quic60_s")
SEEDS = (42, 2025, 3407)


def load_config(name: str) -> dict:
    with (ROOT / "configs" / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_aggregator():
    """Import scripts/aggregate_evidence.py without needing it on sys.path."""
    path = ROOT / "scripts" / "aggregate_evidence.py"
    spec = importlib.util.spec_from_file_location("aggregate_evidence", path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["aggregate_evidence"] = module
    spec.loader.exec_module(module)
    return module


def load_script(name: str):
    """Import a script from scripts/ by file name (no package context)."""
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


class RebuiltAblationConfigTests(unittest.TestCase):
    """The rebuilt No Attention config must be comparable to the main runs."""

    def setUp(self):
        self.cfg = load_config("hsta_no_attention_v13.yaml")
        self.main = load_config("hsta_flash.yaml")
        self.base_cfg = self.cfg["base"]["model_cfg"]

    def test_covers_four_tasks_and_three_seeds(self):
        self.assertEqual(len(self.cfg["experiments"]), 12)
        observed = {
            (task, int(exp.get("seed", self.cfg["base"]["seed"])))
            for exp in self.cfg["experiments"]
            for task in TASKS
            if task in exp["exp_name"]
        }
        expected = {(task, seed) for task in TASKS for seed in SEEDS}
        self.assertEqual(observed, expected)

    def test_attention_backend_matches_the_main_experiment(self):
        """The original config omitted this and silently fell back to 'manual'."""
        self.assertEqual(
            self.base_cfg["attention_backend"],
            self.main["base"]["model_cfg"]["attention_backend"],
            "the no-attention control must run on the same attention backend as HSTA",
        )

    def test_layout_replaces_attention_with_a_third_ffn(self):
        layout = self.base_cfg["layout"]
        self.assertEqual(layout, ["mamba", "mamba", "mlp", "mlp", "mlp"])
        self.assertNotIn("attention", layout)
        # Depth is held constant at 5 blocks, matching the main HSTA stack.
        self.assertEqual(len(layout), len(self.main["base"]["model_cfg"]["layout"]))

    def test_all_other_settings_match_the_main_experiment(self):
        main_cfg = self.main["base"]["model_cfg"]
        for key in ("dim", "heads", "mlp_ratio", "dropout", "d_state", "d_conv",
                    "expand", "pooling", "max_len"):
            self.assertEqual(self.base_cfg[key], main_cfg[key],
                             f"{key} differs from the main experiment")

    def test_output_dir_is_new_and_cannot_clobber_earlier_artefacts(self):
        self.assertNotEqual(self.cfg["base"]["output_dir"],
                            load_config("hsta_no_attention.yaml")["base"]["output_dir"])
        self.assertIn("v13", self.cfg["base"]["output_dir"])


class LegacyConfigDefectTests(unittest.TestCase):
    """Documents the state that made the Table 4 row untraceable."""

    def test_legacy_config_omits_the_attention_backend(self):
        # This is the defect, not an endorsement. If the legacy config is ever
        # repaired, delete this test together with the legacy config.
        legacy = load_config("hsta_no_attention.yaml")
        self.assertNotIn("attention_backend", legacy["base"]["model_cfg"])
        main = load_config("hsta_flash.yaml")
        self.assertEqual(main["base"]["model_cfg"]["attention_backend"], "flash")


class AggregatorStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.agg = load_aggregator()

    def test_sign_test_floor_at_three_pairs_is_025(self):
        """3 seeds can never reach p<0.05 -- the reason it is not the primary test."""
        a = [0.92, 0.93, 0.94]
        b = [0.90, 0.91, 0.92]
        method, _stat, p, n = self.agg.paired_test(a, b)
        self.assertEqual(n, 3)
        self.assertAlmostEqual(p, 0.25, places=6)
        # Reported as a sign test, never as a Wilcoxon p-value.
        self.assertIn("sign-test", method)

    def test_paired_test_reports_wilcoxon_only_from_six_pairs(self):
        a = [0.90 + 0.01 * i for i in range(6)]
        b = [0.90] * 6
        method, _stat, p, n = self.agg.paired_test(a, b)
        self.assertEqual(n, 6)
        self.assertEqual(method, "wilcoxon")
        # SciPy's exact two-sided Wilcoxon test has a 0.0625 floor for six
        # identical-sign differences; the exact sign-test floor is different.
        self.assertAlmostEqual(p, 0.0625, places=6)

    def test_paired_test_handles_all_zero_differences(self):
        method, _stat, p, n = self.agg.paired_test([0.9, 0.9], [0.9, 0.9])
        self.assertEqual(n, 0)
        self.assertEqual(p, 1.0)
        self.assertIn("all-zero", method)

    def test_welch_detects_a_large_gap_and_not_a_tiny_one(self):
        big = self.agg.welch_t([0.95, 0.95, 0.95], [0.85, 0.85, 0.85])
        self.assertIsNotNone(big)
        self.assertLess(big[2], 0.01)

        tiny = self.agg.welch_t([0.950, 0.951, 0.949], [0.950, 0.949, 0.951])
        self.assertIsNotNone(tiny)
        self.assertGreater(tiny[2], 0.05)

    def test_task_and_seed_parsing(self):
        self.assertEqual(self.agg.task_of("hsta_flash_quic40_s_seed42"), "quic40_s")
        self.assertEqual(self.agg.task_of("alignment_baselines_v13_tls60_s_seed3407"),
                         "tls60_s")
        self.assertEqual(self.agg.seed_of("hsta_flash_tls40_s_seed2025"), 2025)


class AggregatorDiscoveryTests(unittest.TestCase):
    """End-to-end check against a synthetic results tree."""

    def setUp(self):
        self.agg = load_aggregator()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_run(self, directory: str, run: str, seed: int, f1: float,
                   params: int = 602408, backend: str = "flash") -> None:
        run_dir = self.root / directory / run
        run_dir.mkdir(parents=True, exist_ok=True)
        payload = {"result": {
            "exp_name": run, "seed": seed,
            "test_accuracy": f1 + 0.004, "test_macro_f1": f1,
            "test_macro_precision": f1, "test_macro_recall": f1,
            "total_params": params, "attention_backend_actual": backend,
        }}
        (run_dir / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_labels_and_summarises_known_variants(self):
        for seed in SEEDS:
            self._write_run("hsta_flash", f"hsta_flash_quic40_s_seed{seed}", seed, 0.9122)
            self._write_run("hsta_no_attention_v13",
                            f"ablation_v13_no_attention_quic40_s_seed{seed}", seed, 0.8918)

        df = self.agg.load_runs(self.root)
        self.assertEqual(len(df), 6)

        df["variant"] = df.apply(self.agg.variant_label, axis=1)
        self.assertEqual(set(df["variant"]), {"HSTA", "No Attention (v13)"})

        summary = self.agg.summarise(df)
        hsta = summary[(summary["variant"] == "HSTA") & (summary["task"] == "quic40_s")]
        self.assertAlmostEqual(float(hsta["f1_mean"].iloc[0]), 91.22, places=6)

        pair = self.agg.pairwise(summary, df)
        self.assertEqual(len(pair), 1)
        self.assertAlmostEqual(float(pair["delta_pp"].iloc[0]), 2.04, places=6)
        # 3 shared seeds -> the paired test must be labelled as a sign test.
        self.assertIn("sign-test", str(pair["paired_method"].iloc[0]))

    def test_coverage_flags_missing_ablation(self):
        for seed in SEEDS:
            self._write_run("hsta_flash", f"hsta_flash_tls40_s_seed{seed}", seed, 0.9667)
        df = self.agg.load_runs(self.root)
        cov = self.agg.coverage(df)

        no_attn = cov[cov["variant"] == "No Attention (v13)"]
        self.assertEqual(len(no_attn), 4)
        self.assertTrue((no_attn["status"] == "MISSING/INCOMPLETE").all())
        self.assertTrue((no_attn["runs_found"] == 0).all())

        hsta_tls40 = cov[(cov["variant"] == "HSTA") & (cov["task"] == "TLS-40")]
        self.assertEqual(hsta_tls40["status"].iloc[0], "OK")

    def test_alignment_runs_are_picked_up_by_name(self):
        self._write_run("alignment_baselines_v13",
                        "alignv13_transformer_d3_quic40_s_seed42", 42, 0.8950)
        df = self.agg.load_runs(self.root)
        df["variant"] = df.apply(self.agg.variant_label, axis=1)
        self.assertEqual(set(df["variant"]), {"aligned:transformer_d3"})

    def test_unreadable_metrics_are_skipped_not_fatal(self):
        (self.root / "hsta_flash" / "broken").mkdir(parents=True)
        (self.root / "hsta_flash" / "broken" / "metrics.json").write_text(
            "{not valid json", encoding="utf-8")
        self._write_run("hsta_flash", "hsta_flash_quic40_s_seed42", 42, 0.90)

        df = self.agg.load_runs(self.root)
        self.assertEqual(len(df), 1)


class RatioStudyConfigTests(unittest.TestCase):
    """The ratio study must isolate the ratio from the placement."""

    def setUp(self):
        self.cfg = load_config("ratio_scale_v13.yaml")
        self.base_cfg = self.cfg["base"]["model_cfg"]
        self.main = load_config("hsta_flash.yaml")

    @staticmethod
    def _counts(layout) -> tuple[int, int]:
        parts = [str(p).lower() for p in layout]
        return (sum(1 for p in parts if p == "mamba"),
                sum(1 for p in parts if p == "attention"))

    def test_covers_the_five_intended_arms(self):
        ratios = set()
        for exp in self.cfg["experiments"]:
            m, a = self._counts(exp["model_cfg"]["layout"])
            ratios.add(f"{m}:{a}" if a else f"{m}:0")
        self.assertEqual(ratios, {"1:0", "1:1", "2:1", "3:1", "4:1"})

    @staticmethod
    def _task_of(name: str) -> str | None:
        m = re.search(r"(quic40_s|quic60_s|tls40_s|tls60_s)", name)
        return m.group(1) if m else None

    def test_sixty_runs_across_three_tiers(self):
        # 60-class only for the full arm sweep; 40-class kept as a small ladder.
        per_task: dict[str, int] = {}
        for exp in self.cfg["experiments"]:
            task = self._task_of(exp["exp_name"])
            per_task[task] = per_task.get(task, 0) + 1
        self.assertEqual(sum(per_task.values()), 60)
        self.assertEqual(per_task.get("quic60_s"), 30)   # Tier A: 5 arms x 6 seeds
        self.assertEqual(per_task.get("tls60_s"), 18)    # Tier B: 3 arms x 6 seeds
        self.assertEqual(per_task.get("quic40_s"), 12)   # Tier C: 2 arms x 6 seeds
        self.assertIsNone(per_task.get("tls40_s"),
                          "tls40_s should not be run: 40-class is a subset ladder only")

    def test_six_seeds_on_every_arm(self):
        """n=3 cannot reach p<0.05; the study must run 6 seeds."""
        seeds = {int(exp["seed"]) for exp in self.cfg["experiments"]}
        self.assertEqual(seeds, {42, 2025, 3407, 1337, 7, 2024})
        self.assertGreaterEqual(len(seeds), 6)

    def test_total_run_count(self):
        # 30 (QUIC-60, 5 arms) + 18 (TLS-60, 3 arms) + 12 (QUIC-40 ladder) = 60
        self.assertEqual(len(self.cfg["experiments"]), 60)

    def test_every_training_setting_matches_the_published_protocol(self):
        for key in ("dim", "heads", "mlp_ratio", "dropout", "d_state", "d_conv",
                    "expand", "pooling", "max_len"):
            self.assertEqual(self.base_cfg[key],
                             self.main["base"]["model_cfg"][key],
                             f"{key} differs from the published HSTA protocol")

    def test_attention_placement_is_identical_in_every_arm(self):
        """The whole point: only the block COUNT changes, never the order."""
        for exp in self.cfg["experiments"]:
            layout = [str(p).lower() for p in exp["model_cfg"]["layout"]]
            m, a = self._counts(layout)
            # Mamba blocks form one contiguous stack at the front.
            self.assertEqual(layout[:m], ["mamba"] * m,
                             f"{exp['exp_name']}: mamba blocks are not leading")
            if a == 0:
                # No-attention arm is just the state-space stack plus one FFN.
                self.assertEqual(layout, ["mamba"] * m + ["mlp"])
                continue
            # Exactly one FFN separates the state-space stack from the attention.
            self.assertEqual(layout[m], "mlp", f"{exp['exp_name']}: missing gate FFN")
            # Exactly one attention block, immediately after that FFN.
            self.assertEqual(layout[m + 1], "attention",
                             f"{exp['exp_name']}: attention is not post-transformation")
            self.assertEqual(a, 1, f"{exp['exp_name']}: expected a single attention block")
            # Trailing FFN closes the sequence.
            self.assertEqual(layout[-1], "mlp", f"{exp['exp_name']}: missing trailing FFN")

    def test_all_experiments_declare_the_flash_backend_where_it_matters(self):
        # The base config must pin the backend; arms inherit it rather than
        # silently falling back to the model default, which is the defect that
        # made the legacy no-attention config incomparable.
        self.assertEqual(self.base_cfg["attention_backend"], "flash")

    def test_output_dir_is_distinct_from_other_evidence_runs(self):
        self.assertEqual(self.cfg["base"]["output_dir"], "results/ratio_scale_v13")


class RatioBudgetConfigTests(unittest.TestCase):
    """The controlled-budget study must actually match widths by arm."""

    def setUp(self):
        self.cfg = load_config("ratio_budget_v13.yaml")

    def test_has_three_arms_and_six_seeds(self):
        self.assertEqual(len(self.cfg["experiments"]), 18)
        seeds = {int(exp["seed"]) for exp in self.cfg["experiments"]}
        self.assertEqual(seeds, {42, 2025, 3407, 1337, 7, 2024})

    def test_each_arm_uses_the_declared_parameter_matching_width(self):
        expected_dims = {"m2a1": 128, "m3a1": 116, "m2a2": 112}
        counts = {key: 0 for key in expected_dims}
        for exp in self.cfg["experiments"]:
            arm = next(key for key in expected_dims if key in exp["exp_name"])
            counts[arm] += 1
            self.assertEqual(exp["model_cfg"]["dim"], expected_dims[arm])
        self.assertEqual(counts, {key: 6 for key in expected_dims})

    def test_ratio_budget_layouts_match_their_arm_names(self):
        for exp in self.cfg["experiments"]:
            name = exp["exp_name"]
            layout = [str(part).lower() for part in exp["model_cfg"]["layout"]]
            mamba = layout.count("mamba")
            attention = layout.count("attention")
            if "m2a1" in name:
                self.assertEqual((mamba, attention), (2, 1))
            elif "m3a1" in name:
                self.assertEqual((mamba, attention), (3, 1))
            elif "m2a2" in name:
                self.assertEqual((mamba, attention), (2, 2))
            else:
                self.fail(f"unexpected ratio-budget arm: {name}")

    def test_flash_backend_is_pinned(self):
        self.assertEqual(self.cfg["base"]["model_cfg"]["attention_backend"], "flash")


class RatioCalculatorTests(unittest.TestCase):
    """The analytic calculator must agree with the measured parameter counts."""

    def setUp(self):
        self.calc = load_script("ratio_calculator.py")

    def test_block_sizes_are_ordered_as_expected(self):
        mp = self.calc.mamba_params(128)
        ap = self.calc.attention_params(128)
        fp = self.calc.mlp_params(128)
        self.assertGreater(mp, 0)
        self.assertGreater(fp, mp)
        self.assertGreater(mp, ap)

    def test_calculated_params_match_the_stored_run_records(self):
        cases = [
            (2, 1, 2, 40, 602408),
            (2, 1, 2, 60, 604988),
        ]
        for m, a, mlp, cls, observed in cases:
            with self.subTest(classes=cls):
                calc = self.calc.total_params(m, a, mlp, cls)
                err = abs(calc - observed) / observed
                self.assertLess(err, 0.05,
                                f"calculator off by {err * 100:.1f}% for {cls} classes")

    def test_mamba_share_costs_more_parameters_at_equal_width(self):
        """The fixed-width ratio sweep grows with each added Mamba block."""
        p_1to1 = self.calc.total_params(1, 1, 2, 40)
        p_2to1 = self.calc.total_params(2, 1, 3, 40)
        self.assertGreater(p_2to1, p_1to1)

    def test_scaling_is_quadratic_in_width(self):
        ratio = (self.calc.mamba_params(256) / self.calc.mamba_params(128))
        self.assertAlmostEqual(ratio, 4.0, delta=0.6)


class RunnerCliTests(unittest.TestCase):
    def test_run_experiments_supports_isolated_output_dir(self):
        source = (ROOT / "run_experiments.py").read_text(encoding="utf-8")
        self.assertIn("--output-dir", source)
        # The override must be applied to base before experiments are merged.
        self.assertLess(source.index("base[\"output_dir\"] = args.output_dir"),
                        source.index("_merge_experiment(base, exp)"))

    def test_evidence_runner_exposes_expected_modes(self):
        runner = (ROOT / "scripts" / "run_evidence_pack.sh").read_text(encoding="utf-8")
        for mode in ("probe", "stage_ablation", "stage_alignment", "stage_all",
                     "parallel_ablation", "parallel_alignment", "report"):
            self.assertIn(mode, runner)
        # Parallel workers must isolate BOTH the aggregated CSV and the
        # per-run artefacts, otherwise --resume can skip a run another worker
        # is still writing.
        self.assertIn("--output-dir", runner)
        self.assertIn("_scratch_", runner)
        self.assertIn("logs/_scratch_", runner)
        self.assertIn("Consolidated", runner)


if __name__ == "__main__":
    unittest.main()
