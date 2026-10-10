"""Audit a processed open-set CSV before it is used for formal results."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


REQUIRED = {
    "flow_id", "label", "split", "pkt_index", "size", "direction", "delta_time",
    "source_group", "original_app", "noise_family",
}
def audit(path: Path, expected_known: int = 60) -> dict:
    """Validate an open-set export and its provenance metadata.

    ``expected_known`` defaults to the active 60-class small protocol.
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
            label = str(row["label"])
            group = str(row.get("source_group", "") or "")
            app = str(row.get("original_app", "") or "")
            family = str(row.get("noise_family", "") or "")
            labels.add(label)
            split_flow_ids[split].add(flow_id)
            first = flows.setdefault(flow_id, {"split": split, "label": label, "source_group": group, "original_app": app, "noise_family": family})
            if first != {"split": split, "label": label, "source_group": group, "original_app": app, "noise_family": family}:
                raise ValueError(f"flow {flow_id} has inconsistent metadata")
            if label == "unknown" and app and not app.startswith("synthetic_noise::"):
                app_groups[app].add(group)
            if group.startswith("noise_"):
                noise_families[split].add(family)

    intersections = {
        "flow_id_split_intersections": {
            f"{left}:{right}": sorted(split_flow_ids[left] & split_flow_ids[right])[:10]
            for left, right in (("train", "val"), ("train", "test"), ("val", "test"))
            if split_flow_ids[left] & split_flow_ids[right]
        },
        "application_group_conflicts": {app: sorted(groups) for app, groups in app_groups.items() if len(groups) > 1},
    }
    if intersections["flow_id_split_intersections"] or intersections["application_group_conflicts"]:
        raise ValueError(json.dumps(intersections, ensure_ascii=False))
    family_sets = [values for values in noise_families.values() if values]
    if len(family_sets) != len({family for values in family_sets for family in values}):
        raise ValueError("noise_family is reused across train/val/test")

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
