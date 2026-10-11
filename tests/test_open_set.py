from data.open_set import open_set_metrics, unknown_score_from_logits
from train import eval_model


def test_unknown_metrics_use_explicit_reject_class():
    metrics = open_set_metrics(
        [0, 1, 2, 2],
        [0, 2, 2, 1],
        logits=[[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0], [0.0, 4.0, 0.0]],
        classes=["known-a", "known-b", "unknown"],
    )
    assert metrics["unknown_index"] == 2
    assert metrics["unknown_recall"] == 0.5
    assert metrics["known_false_unknown_rate"] == 0.5
    assert metrics["unknown_false_known_rate"] == 0.5
    assert 0.0 <= metrics["unknown_aupr"] <= 1.0
    assert metrics["known_macro_f1"] == 0.5


def test_closed_set_unknown_score_uses_one_minus_max_probability():
    scores = unknown_score_from_logits([[8.0, 0.0], [0.0, 0.0]])
    assert scores[0] < scores[1]
    metrics = open_set_metrics(
        [0, 1, 2],
        [0, 0, 1],
        logits=[[8.0, 0.0], [8.0, 0.0], [0.0, 0.0]],
        classes=["known-a", "known-b", "unknown"],
        unknown_index=2,
        reject_threshold=0.25,
    )
    assert metrics["unknown_recall"] == 1.0
    assert metrics["unknown_false_known_rate"] == 0.0
    assert metrics["unknown_aupr"] >= 0.0


def test_eval_persists_raw_and_threshold_metric_names():
    class FixedModel:
        def eval(self):
            return self

        def __call__(self, x):
            import torch

            return torch.tensor([[4.0, 0.0, 0.0], [0.0, 1.0, 2.0]], device=x.device)

    import torch

    loader = [(torch.zeros((2, 1, 1)), torch.tensor([0, 2]))]
    metrics, _, _ = eval_model(
        FixedModel(),
        loader,
        "cpu",
        unknown_index=2,
        classes=["known-a", "known-b", "unknown"],
        reject_threshold=0.5,
    )
    for prefix in ("raw", "threshold"):
        assert f"{prefix}_unknown_auroc" in metrics
        assert f"{prefix}_unknown_aupr" in metrics
        assert f"{prefix}_unknown_false_known_rate" in metrics
        assert f"{prefix}_known_macro_f1" in metrics
        assert f"{prefix}_open_set_macro_f1" in metrics


def test_open_threshold_uses_calibrated_rule_instead_of_unknown_argmax():
    # Unknown wins argmax, but stays below the specified operating threshold.
    metrics = open_set_metrics([0, 2], [2, 2], [[1., 0., 2.], [0., 0., 9.]],
                               classes=["a", "b", "unknown"], reject_threshold=0.9)
    assert metrics["known_false_unknown_rate"] == 0.0
    assert metrics["unknown_recall"] == 1.0
