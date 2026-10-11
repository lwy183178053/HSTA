import csv

import pytest

from scripts.audit_open_set_dataset import audit


FIELDS = [
    "flow_id", "label", "split", "pkt_index", "size", "direction", "delta_time",
    "source", "source_group", "original_app", "noise_family", "capture_date", "source_flow_id",
]


def _write_valid_fixture(path, duplicate_source=False):
    dates = {
        "train": "20211004",
        "val": "20211011",
        "test": "20211012",
    }
    rows = []
    for split in ("train", "val", "test"):
        unknown_group = {
            "train": "unknown_support",
            "val": "unknown_val_heldout",
            "test": "unknown_test_heldout",
        }[split]
        for label, group, app, source, family in (
            ("known", "known", "known-app", "datazoo", ""),
            ("unknown", unknown_group, f"{split}-unknown-app", "datazoo", ""),
            ("unknown", f"noise_{split}", "synthetic_noise::family", "synthetic_noise", f"{split}-family"),
        ):
            flow_id = f"{split}-{group}"
            source_flow_id = f"source-{split}-{group}"
            if duplicate_source and split == "train" and group == "known":
                source_flow_id = "source-train-known"
            for pkt_index in range(30):
                rows.append({
                    "flow_id": flow_id,
                    "label": label,
                    "split": split,
                    "pkt_index": pkt_index,
                    "size": 1,
                    "direction": 1,
                    "delta_time": 1,
                    "source": source,
                    "source_group": group,
                    "original_app": app,
                    "noise_family": family,
                    "capture_date": "" if source == "synthetic_noise" else dates[split],
                    "source_flow_id": source_flow_id,
                })
    if duplicate_source:
        for pkt_index in range(30):
            rows.append({
                "flow_id": "train-known-duplicate",
                "label": "known",
                "split": "train",
                "pkt_index": pkt_index,
                "size": 1,
                "direction": 1,
                "delta_time": 1,
                "source": "datazoo",
                "source_group": "known",
                "original_app": "known-app",
                "noise_family": "",
                "capture_date": dates["train"],
                "source_flow_id": "source-train-known",
            })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_audit_accepts_packet_rows_sharing_one_source_flow_id(tmp_path):
    path = tmp_path / "tls_fixture.csv"
    _write_valid_fixture(path)

    result = audit(path, expected_known=1)

    assert result["audit_passed"] is True


def test_audit_rejects_source_flow_id_reused_by_distinct_flows(tmp_path):
    path = tmp_path / "tls_fixture.csv"
    _write_valid_fixture(path, duplicate_source=True)

    with pytest.raises(ValueError, match="duplicate source_flow_id within train"):
        audit(path, expected_known=1)
