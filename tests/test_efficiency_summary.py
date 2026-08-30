import tempfile
import unittest
from pathlib import Path

import pandas as pd
import torch

from benchmark_efficiency import estimate_flops
from models import build_model
from scripts.summarize_paper_main_results import MODEL_ORDER, TASK_ORDER, summarize_results


class RecentEfficiencyTests(unittest.TestCase):
    def test_recent_models_include_non_module_operations_in_flops(self):
        expectations = {
            "srvit": "attention_matmul_softmax",
            "trafficaudio": "mfcc_stft_mel_dct",
            "bpf_gnn": "graph_message_passing",
        }
        for name, expected_key in expectations.items():
            with self.subTest(model=name):
                model = build_model(name, 3, 40, 30, {"dim": 32, "dropout": 0.0})
                flops, breakdown = estimate_flops(
                    model, torch.randn(1, 30, 3), estimate_mamba_scan=True, amp=False
                )
                self.assertGreater(flops, 0)
                self.assertIn(expected_key, breakdown)
                self.assertGreater(breakdown[expected_key], 0)


class PaperMainSummaryTests(unittest.TestCase):
    def test_summary_keeps_exactly_eight_models_and_three_seeds(self):
        prefixes = {
            "GRU": "gru_5layer",
            "Transformer": "transformer_5layer",
            "30pktTCNET": "30pkttcnet_adapted",
            "NetMamba": "netmamba_adapted",
            "SRViT": "srvit",
            "TrafficAudio": "trafficaudio",
            "BPF-GNN": "bpf_gnn",
            "HSTA": "hsta_flash",
        }
        rows = []
        for model_index, model in enumerate(MODEL_ORDER):
            for task in TASK_ORDER:
                for seed_index, seed in enumerate((42, 2025, 3407)):
                    value = 0.80 + model_index * 0.01 + seed_index * 0.001
                    rows.append(
                        {
                            "exp_name": (
                                f"{prefixes[model]}_{task}"
                                if model == "GRU" and seed == 42
                                else f"{prefixes[model]}_{task}_seed{seed}"
                            ),
                            "test_accuracy": value + 0.002,
                            "test_macro_precision": value + 0.001,
                            "test_macro_recall": value,
                            "test_macro_f1": value,
                        }
                    )
        rows.append(
            {
                "exp_name": "mlp_tls40_s_seed42",
                "test_accuracy": 0.99,
                "test_macro_precision": 0.99,
                "test_macro_recall": 0.99,
                "test_macro_f1": 0.99,
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "all.csv"
            pd.DataFrame(rows).to_csv(source, index=False)
            summary = summarize_results([source])

        self.assertEqual(summary["model"].drop_duplicates().tolist(), list(MODEL_ORDER))
        self.assertEqual(summary["task"].drop_duplicates().tolist(), list(TASK_ORDER))
        self.assertEqual(len(summary), len(MODEL_ORDER) * len(TASK_ORDER))
        self.assertTrue((summary["effective_seeds"] == 3).all())
        self.assertNotIn("MLP", set(summary["model"]))


if __name__ == "__main__":
    unittest.main()
