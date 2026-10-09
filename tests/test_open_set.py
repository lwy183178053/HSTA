from data.open_set import open_set_metrics


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
