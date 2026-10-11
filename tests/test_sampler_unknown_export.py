"""Regression tests for complete real-unknown export handling."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from data.sampler import _include_validation_unknowns, export_csv


def _batch(labels: list[str]):
    # iter_batch reads PPI from field 1 and labels from field 3.
    ppi = np.asarray(
        [
            [[0.1, 0.2], [1.0, 1.0], [10.0, 20.0]]
            for _ in labels
        ],
        dtype=np.float32,
    )
    return (None, ppi, None, np.asarray(labels, dtype=object))


class _LoaderDataset:
    class_info = SimpleNamespace()

    def __init__(self):
        # Test ordering mirrors DataZoo: known flows precede unknown flows.
        self._loaders = {
            "train": [_batch(["known_a"])],
            "val": [_batch(["known_a", "unknown_val_app"])],
            "test": [_batch(["known_a", "unknown_test_app"])],
        }

    def get_train_dataloader(self):
        return self._loaders["train"]

    def get_val_dataloader(self):
        return self._loaders["val"]

    def get_test_dataloader(self):
        return self._loaders["test"]


def test_export_scans_past_known_prefix_and_keeps_unknown_metadata(tmp_path):
    dataset = _LoaderDataset()
    out_csv = tmp_path / "export.csv"
    counts, _, _ = export_csv(
        dataset,
        out_csv,
        classes=["known_a"],
        seq_len=2,
        max_per_class_by_split={"train": 1, "val": 1, "test": 1},
        include_unknown=True,
        unknown_source_groups={
            "unknown_support": ["unknown_train_app"],
            "unknown_val_heldout": ["unknown_val_app"],
            "unknown_test_heldout": ["unknown_test_app"],
        },
    )
    # The unknown item follows the known item in each combined batch and must
    # still be exported after the known class reaches its cap.
    assert counts["val"]["unknown"] == 1
    assert counts["test"]["unknown"] == 1
    rows = out_csv.read_text(encoding="utf-8-sig")
    assert "unknown_val_app" in rows
    assert "unknown_test_app" in rows
    assert "unknown_val_heldout" in rows
    assert "unknown_test_heldout" in rows


def test_validation_indices_are_combined_with_unknown_indices():
    known = np.array([(0, 1), (0, 2)], dtype=[("TABLE", "i4"), ("INDEX", "i4")])
    unknown = np.array([(0, 9)], dtype=known.dtype)
    dataset = SimpleNamespace(
        val_dataset=SimpleNamespace(indices=known.copy()),
        val_dataloader=object(),
        dataset_indices=SimpleNamespace(val_known_indices=known, val_unknown_indices=unknown),
    )
    assert _include_validation_unknowns(dataset) == 1
    assert dataset.val_dataset.indices.tolist() == [(0, 1), (0, 2), (0, 9)]
    assert dataset.val_dataloader is None
    assert dataset._hsta_val_includes_unknown is True
