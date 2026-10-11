"""Audit a processed open-set CSV before it is used for formal results."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


REQUIRED = {
    "flow_id", "label", "split", "pkt_index", "size", "direction", "delta_time",
    "source", "source_group", "original_app", "noise_family", "capture_date", "source_flow_id",
}
DATE_SPLITS = {
    "tls": {
        "train": {f"202110{day:02d}" for day in range(4, 11)},
        "val": {"20211011"},
        "test": {f"202110{day:02d}" for day in range(12, 18)},
    },
    "quic": {
        "train": {"20221031"} | {f"202211{day:02d}" for day in range(1, 14)},
        "val": {"20221114", "20221115"},
        "test": {f"202211{day:02d}" for day in range(16, 28)},
    },
}
def audit(path: Path, expected_known: int = 60) -> dict:
    """Validate an open-set export and its provenance metadata.

    ``expected_known`` defaults to the active 60-class protocol.
    Other protocols can pass their actual number of known classes explicitly.
    """
    if expected_known < 1:
        raise ValueError("expected_known must be positive")
    flows: dict[str, dict[str, str]] = {}
    split_flow_ids: dict[str, set[str]] = defaultdict(set)
    app_groups: dict[str, set[str]] = defaultdict(set)
    noise_families: dict[str, set[str]] = defaultdict(set)
    labels: set[str] = set()
    packet_rows = 0
    flow_packet_counts: dict[str, int] = defaultdict(int)
    flow_dates: dict[str, str] = {}
    source_ids: dict[str, str] = {}
    source_ids_by_split: dict[str, dict[str, str]] = defaultdict(dict)
    dataset_name = "quic" if "quic" in path.name.lower() else "tls"
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED - fields)
        if missing:
            raise ValueError(f"missing required columns: {missing}")
        for row in reader:
            packet_rows += 1
            flow_id = str(row["flow_id"])
            split = str(row["split"]).lower()
            if split not in {"train", "val", "test"}:
                raise ValueError(f"invalid split {split!r}")
            try:
                for value in (row["size"], row["direction"], row["delta_time"]):
                    if not (float(value) == float(value)):
                        raise ValueError
                packet_index = int(row["pkt_index"])
            except (TypeError, ValueError):
                raise ValueError(f"invalid numeric packet row for {flow_id}")
            if not 0 <= packet_index < 30:
                raise ValueError(f"pkt_index out of range: {packet_index}")
            date = str(row.get("date", row.get("capture_date", "")))
            is_synthetic = str(row.get("source", "")) == "synthetic_noise"
            if not is_synthetic and date not in DATE_SPLITS[dataset_name][split]:
                raise ValueError(f"capture_date {date!r} outside {dataset_name}/{split} window")
            if is_synthetic and date:
                raise ValueError("synthetic noise must not carry a capture date")
            source_id = str(row.get("source_flow_id", ""))
            if not source_id:
                raise ValueError(f"missing source_flow_id for {flow_id}")
            label = str(row["label"])
            group = str(row.get("source_group", "") or "")
            app = str(row.get("original_app", "") or "")
            family = str(row.get("noise_family", "") or "")
            labels.add(label)
            split_flow_ids[split].add(flow_id)
            flow_packet_counts[flow_id] += 1
            if date:
                flow_dates[flow_id] = date
            previous_source_id = source_ids.get(flow_id)
            if previous_source_id is not None and previous_source_id != source_id:
                raise ValueError(f"flow {flow_id} has inconsistent source_flow_id")
            source_ids[flow_id] = source_id
            previous_flow_id = source_ids_by_split[split].get(source_id)
            if previous_flow_id is not None and previous_flow_id != flow_id:
                raise ValueError(f"duplicate source_flow_id within {split}: {source_id}")
            source_ids_by_split[split][source_id] = flow_id
            first = flows.setdefault(flow_id, {"split": split, "label": label, "source_group": group, "original_app": app, "noise_family": family})
            if first != {"split": split, "label": label, "source_group": group, "original_app": app, "noise_family": family}:
                raise ValueError(f"flow {flow_id} has inconsistent metadata")
            if label == "unknown" and app and not app.startswith("synthetic_noise::"):
                app_groups[app].add(group)
            if group.startswith("noise_"):
                noise_families[split].add(family)

    source_split_ids = {split: {source_ids[flow_id] for flow_id in ids} for split, ids in split_flow_ids.items()}
    intersections = {
        "flow_id_split_intersections": {
            f"{left}:{right}": sorted(split_flow_ids[left] & split_flow_ids[right])[:10]
            for left, right in (("train", "val"), ("train", "test"), ("val", "test"))
            if split_flow_ids[left] & split_flow_ids[right]
        },
        "source_flow_id_split_intersections": {
            f"{left}:{right}": sorted(source_split_ids[left] & source_split_ids[right])[:10]
            for left, right in (("train", "val"), ("train", "test"), ("val", "test"))
            if source_split_ids[left] & source_split_ids[right]
        },
        "application_group_conflicts": {app: sorted(groups) for app, groups in app_groups.items() if len(groups) > 1},
    }
    if intersections["flow_id_split_intersections"] or intersections["source_flow_id_split_intersections"] or intersections["application_group_conflicts"]:
        raise ValueError(json.dumps(intersections, ensure_ascii=False))
    family_sets = [noise_families.get(split, set()) for split in ("train", "val", "test")]
    if any(left & right for i, left in enumerate(family_sets) for right in family_sets[i + 1:]):
        raise ValueError("noise_family is reused across train/val/test")
    bad_lengths = {flow_id: count for flow_id, count in flow_packet_counts.items() if count != 30}
    if bad_lengths:
        raise ValueError(f"flows must contain exactly 30 packets: {list(bad_lengths.items())[:3]}")

    source_by_split = {
        split: sorted({flows[flow_id]["source_group"] for flow_id in flow_ids})
        for split, flow_ids in sorted(split_flow_ids.items())
    }
    known_labels = labels - {"unknown"}
    if len(known_labels) != expected_known or "unknown" not in labels:
        raise ValueError(
            f"expected {expected_known} known labels plus unknown, "
            f"got {len(known_labels)} known labels"
        )
    missing_train_sources = sorted({"known", "unknown_support", "noise_train"} - set(source_by_split.get("train", [])))
    if missing_train_sources:
        raise ValueError(f"train split missing required source groups: {missing_train_sources}")
    required_test = {"known", "unknown_test_heldout", "noise_test"}
    missing_test_sources = sorted(required_test - set(source_by_split.get("test", [])))
    if missing_test_sources:
        raise ValueError(f"test split missing required source groups: {missing_test_sources}")
    result = {
        "csv": path.as_posix(),
        "packet_rows": packet_rows,
        "flow_count": len(flows),
        "labels": sorted(labels),
        "flow_count_by_split": {split: len(ids) for split, ids in sorted(split_flow_ids.items())},
        "source_groups_by_split": source_by_split,
        "noise_families_by_split": {split: sorted(values) for split, values in sorted(noise_families.items())},
        "application_group_count": len(app_groups),
        "expected_known_labels": expected_known,
        "audit_passed": True,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--expected-known",
        type=int,
        default=60,
        help="expected number of known labels (default: 60)",
    )
    args = parser.parse_args()
    result = audit(args.input_csv, expected_known=args.expected_known)
    report = args.report or args.input_csv.with_suffix(".audit.json")
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
