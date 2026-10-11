import csv
import json
from pathlib import Path

from data.dataset import load_sequence_csv
from scripts.sample_temporal_dataset import sample_dataset


def _write_flows(path: Path) -> None:
    fields = [
        "flow_id",
        "label",
        "pkt_index",
        "size",
        "direction",
        "delta_time",
        "split",
        "source",
        "source_group",
        "original_app",
        "noise_family",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        flows = [
            (f"known-{index}", "known", "", "", "") for index in range(20)
        ] + [
            (f"app-a-{index}", "unknown", "heldout_app", "app-a", "") for index in range(10)
        ] + [
            (f"noise-{index}", "unknown", "synthetic", "", "laplace") for index in range(10)
        ]
        for flow_id, label, source_group, app, family in flows:
            writer.writerow(
                {
                    "flow_id": flow_id,
                    "label": label,
                    "pkt_index": 0,
                    "size": 100,
                    "direction": 1,
                    "delta_time": 0.1,
                    "split": "train",
                    "source": "datazoo" if label != "unknown" else "heldout",
                    "source_group": source_group,
                    "original_app": app,
                    "noise_family": family,
                }
            )


def test_unknown_sampling_is_stratified_and_manifest_is_complete(tmp_path: Path):
    source = tmp_path / "source.csv"
    output = tmp_path / "sample.csv"
    _write_flows(source)

    report = sample_dataset(source, output, "tls", "small", seed=599)
    manifest_path = output.with_suffix(".sampling_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Synthetic rows in the source are intentionally ignored.  The final
    # sampler regenerates the test noise family from the selected known rows.
    assert report["unknown_candidate_group_count"] == 1
    assert manifest["candidate_group_count"] == 2
    unknown_groups = [group for group in manifest["groups"] if group["unknown"]]
    assert {group["source_group"] for group in unknown_groups} == {"heldout_app"}
    assert {group["target_flows"] for group in unknown_groups} == {10}

    with output.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 90
    assert sum(row["label"] == "unknown" for row in rows) == 70
    sampled = load_sequence_csv(output, seq_len=1)
    assert sampled.feature_cols == ["size", "direction", "delta_time"]
    assert sampled.X.shape == (32, 1, 3)


def test_small_profile_caps_match_protocol():
    from scripts.sample_temporal_dataset import PROFILES

    assert PROFILES == {
        "small": {"train": 200, "val": 40, "test": 40},
        "medium": {"train": 2000, "val": 400, "test": 400},
        "large": {"train": 20000, "val": 4000, "test": 4000},
    }


def test_unknown_sampling_falls_back_to_source_for_legacy_csv(tmp_path: Path):
    source = tmp_path / "legacy.csv"
    output = tmp_path / "legacy_sample.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["flow_id", "label", "pkt_index", "size", "direction", "delta_time", "split", "source"],
        )
        writer.writeheader()
        for index in range(2):
            writer.writerow(
                {
                    "flow_id": f"known-{index}",
                    "label": "known",
                    "pkt_index": 0,
                    "size": 100,
                    "direction": 1,
                    "delta_time": 0.1,
                    "split": "train",
                    "source": "datazoo",
                }
            )
        for index in range(2):
            writer.writerow(
                {
                    "flow_id": f"unknown-{index}",
                    "label": "unknown",
                    "pkt_index": 0,
                    "size": 100,
                    "direction": 1,
                    "delta_time": 0.1,
                    "split": "train",
                    "source": "legacy-app",
                }
            )

    report = sample_dataset(source, output, "quic", "small", seed=599)
    manifest = json.loads(output.with_suffix(".sampling_manifest.json").read_text(encoding="utf-8"))
    assert report["unknown_candidate_group_count"] == 1
    group = next(item for item in manifest["groups"] if item["unknown"])
    assert group["source_group"] == "legacy-app"

