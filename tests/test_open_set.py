from data.open_set import open_set_metrics, unknown_score_from_logits


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
