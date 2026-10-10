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
        for flow_id, label, source_group, app, family in [
            ("known-0", "known", "", "", ""),
            ("known-1", "known", "", "", ""),
            ("app-a-0", "unknown", "heldout_app", "app-a", ""),
            ("app-a-1", "unknown", "heldout_app", "app-a", ""),
            ("noise-0", "unknown", "synthetic", "", "laplace"),
            ("noise-1", "unknown", "synthetic", "", "laplace"),
            ("noise-2", "unknown", "synthetic", "", "laplace"),
        ]:
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

    assert report["unknown_candidate_group_count"] == 2
    assert manifest["candidate_group_count"] == 3
    unknown_groups = [group for group in manifest["groups"] if group["unknown"]]
    assert {group["source_group"] for group in unknown_groups} == {"heldout_app", "synthetic"}
    assert all(group["target_flows"] == group["available_flows"] for group in unknown_groups)

    with output.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["flow_id"] for row in rows} == {
        "known-0",
        "known-1",
        "app-a-0",
        "app-a-1",
        "noise-0",
        "noise-1",
        "noise-2",
    }
    sampled = load_sequence_csv(output, seq_len=1)
    assert sampled.feature_cols == ["size", "direction", "delta_time"]
    assert sampled.X.shape == (len(rows), 1, 3)


def test_small_profile_caps_match_protocol():
    from scripts.sample_temporal_dataset import PROFILES

    assert PROFILES == {
        "small": {"train": 100, "val": 20, "test": 20},
        "medium": {"train": 1000, "val": 200, "test": 200},
        "paper": {"train": 10000, "val": 1000, "test": 2000},
    }


def test_unknown_sampling_falls_back_to_source_for_legacy_csv(tmp_path: Path):
    source = tmp_path / "legacy.csv"
    output = tmp_path / "legacy_sample.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["flow_id", "label", "pkt_index", "split", "source"])
        writer.writeheader()
        for index in range(2):
            writer.writerow(
                {
                    "flow_id": f"a-{index}",
                    "label": "unknown",
                    "pkt_index": 0,
                    "split": "train",
                    "source": "legacy-app",
                }
            )

    report = sample_dataset(source, output, "quic", "small", seed=599)
    manifest = json.loads(output.with_suffix(".sampling_manifest.json").read_text(encoding="utf-8"))
    assert report["unknown_candidate_group_count"] == 1
    group = next(item for item in manifest["groups"] if item["unknown"])
    assert group["source_group"] == "legacy-app"

