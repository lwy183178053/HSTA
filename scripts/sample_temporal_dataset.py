"""Create balanced, temporally ordered subsets from a processed S CSV.

The source exporter already assigns disjoint temporal windows to ``train``,
``val`` and ``test``. This utility samples complete flows within each
``(split, label)`` group and each unknown provenance group. No packet from a
selected flow is split across partitions, and the complete candidate and
selection manifest is saved next to the sampled CSV.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


UNKNOWN_LABELS = {"unknown", "_unknown", "__unknown__"}
UNKNOWN_GROUP_COLUMNS = ("source_group", "original_app", "noise_family")


PROFILES = {
    "small": {"train": 100, "val": 20, "test": 20},
    "medium": {"train": 1000, "val": 200, "test": 200},
    "paper": {"train": 10000, "val": 1000, "test": 2000},
    "large": {"train": 10000, "val": 2000, "test": 2000},
}

TEMPORAL_WINDOWS = {
    "tls": {
        "train": "W-2021-40 days 20211004-20211009",
        "val": "W-2021-40 day 20211010",
        "test": "W-2021-41 days 20211011-20211017",
    },
    "quic": {
        "train": "W-2022-44 days 20221031-20221105",
        "val": "W-2022-44 day 20221106",
        "test": "W-2022-45 days 20221107-20221113",
    },
}


def _flow_rows(handle):
    reader = csv.DictReader(handle)
    if not reader.fieldnames:
        raise ValueError("input CSV has no header")
    required = {"flow_id", "label", "split"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise ValueError(f"input CSV is missing columns: {sorted(missing)}")

    current_id = None
    rows = []
    for row in reader:
        flow_id = str(row.get("flow_id", ""))
        if current_id is not None and flow_id != current_id:
            yield current_id, rows
            rows = []
        current_id = flow_id
        rows.append(row)
    if current_id is not None and rows:
        yield current_id, rows


def _rank(seed: int, split: str, label: str, flow_id: str) -> int:
    payload = f"{seed}:{split}:{label}:{flow_id}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


def _value(row: dict[str, str], name: str) -> str:
    """Return a normalized provenance value, treating missing columns as empty."""

    return str(row.get(name, "") or "").strip()


def _is_unknown(label: str) -> bool:
    return str(label).strip().lower() in UNKNOWN_LABELS


def _group_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    """Build a stable sampling group key.

    Known classes remain one group per label. Unknown flows are split by the
    provenance columns written by the exporter. Older CSVs may only contain a
    ``source`` column; that value is used as a compatibility fallback so that
    all unknown rows are still auditable rather than silently merged.
    """

    label = _value(row, "label")
    if not _is_unknown(label):
        return (label, "", "", "")
    source_group = _value(row, "source_group")
    original_app = _value(row, "original_app")
    noise_family = _value(row, "noise_family")
    if not (source_group or original_app or noise_family):
        source_group = _value(row, "source") or "unknown_unattributed"
    return ("unknown", source_group, original_app, noise_family)


def _group_name(key: tuple[str, str, str, str]) -> str:
    label, source_group, original_app, noise_family = key
    if label != "unknown":
        return f"label:{label}"
    parts = [
        f"source_group={source_group or '<missing>'}",
        f"original_app={original_app or '<missing>'}",
        f"noise_family={noise_family or '<missing>'}",
    ]
    return "unknown:" + "|".join(parts)


def _select_ids(input_csv: Path, caps: dict[str, int], seed: int):
    candidates: dict[tuple[str, tuple[str, str, str, str]], list[tuple[int, str]]] = defaultdict(list)
    with input_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        for flow_id, rows in _flow_rows(handle):
            first = rows[0]
            split = str(first["split"]).lower()
            group = _group_key(first)
            if split not in caps:
                continue
            candidates[(split, group)].append((_rank(seed, split, _group_name(group), flow_id), flow_id))

    selected: set[str] = set()
    available = Counter()
    target = Counter()
    manifest_groups = []
    for (split, group), values in sorted(candidates.items(), key=lambda item: (item[0][0], item[0][1])):
        values.sort(key=lambda item: item[0])
        group_name = _group_name(group)
        available[(split, group)] = len(values)
        target[(split, group)] = min(caps[split], len(values))
        selected_values = values[: caps[split]]
        selected.update(flow_id for _, flow_id in selected_values)
        manifest_groups.append(
            {
                "split": split,
                "label": group[0],
                "group": group_name,
                "source_group": group[1],
                "original_app": group[2],
                "noise_family": group[3],
                "unknown": group[0] == "unknown",
                "available_flows": len(values),
                "target_flows": int(target[(split, group)]),
                # Flow-level IDs are useful for auditing unknown provenance
                # isolation. Omitting known-class IDs keeps paper manifests
                # compact while retaining deterministic counts for them.
                "selected_flow_ids": [flow_id for _, flow_id in selected_values]
                if group[0] == "unknown"
                else [],
            }
        )
    return selected, available, target, manifest_groups


def sample_dataset(
    input_csv: Path,
    output_csv: Path,
    dataset: str,
    profile: str,
    seed: int,
) -> dict:
    caps = PROFILES[profile]
    selected, available, target, manifest_groups = _select_ids(input_csv, caps, seed)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    group_counts = Counter()
    packet_rows = 0
    fieldnames = None
    with input_csv.open("r", newline="", encoding="utf-8-sig") as source, output_csv.open(
        "w", newline="", encoding="utf-8"
    ) as destination:
        reader = csv.DictReader(source)
        fieldnames = list(reader.fieldnames or [])
        writer = csv.DictWriter(destination, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        source.seek(0)
        for flow_id, rows in _flow_rows(source):
            if flow_id not in selected:
                continue
            first = rows[0]
            split = str(first["split"]).lower()
            label = str(first["label"])
            group = _group_key(first)
            for row in rows:
                writer.writerow(row)
            packet_rows += len(rows)
            counts[(split, label)] += 1
            group_counts[(split, group)] += 1

    labels = sorted({label for split, label in counts})
    unknown_groups = [item for item in manifest_groups if item["unknown"]]
    available_by_label = Counter()
    target_by_label = Counter()
    for (group_split, group), value in available.items():
        available_by_label[(group_split, group[0])] += int(value)
    for (group_split, group), value in target.items():
        target_by_label[(group_split, group[0])] += int(value)
    manifest_path = output_csv.with_suffix(".sampling_manifest.json")
    manifest = {
        "input_csv": input_csv.as_posix(),
        "output_csv": output_csv.as_posix(),
        "selection_seed": int(seed),
        "sampling_unit": "complete_flow",
        "grouping": {
            "known": "label",
            "unknown": list(UNKNOWN_GROUP_COLUMNS),
            "fallback": "source, then unknown_unattributed",
        },
        "candidate_group_count": len(manifest_groups),
        "unknown_candidate_group_count": len(unknown_groups),
        "groups": manifest_groups,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    source_report = input_csv.with_suffix(".report.json")
    source_metadata = {}
    if source_report.exists():
        try:
            source_metadata = json.loads(source_report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            source_metadata = {}

    def _counter_by_group(counter: Counter, split: str) -> dict[str, int]:
        return {
            _group_name(group): int(value)
            for (group_split, group), value in sorted(counter.items(), key=lambda item: item[0][1])
            if group_split == split
        }

    report = {
        "source_csv": input_csv.as_posix(),
        "out_csv": output_csv.as_posix(),
        "dataset": dataset,
        "size": "S",
        "profile": profile,
        "selection_seed": int(seed),
        "sampling_unit": "complete_flow",
        "caps_per_class": caps,
        "caps_per_group": caps,
        "unknown_grouping": list(UNKNOWN_GROUP_COLUMNS),
        "unknown_group_fallback": "source, then unknown_unattributed",
        "sampling_manifest": manifest_path.as_posix(),
        "candidate_group_count": len(manifest_groups),
        "unknown_candidate_group_count": len(unknown_groups),
        "unknown_candidate_groups": [
            {
                key: value
                for key, value in item.items()
                if key != "selected_flow_ids"
            }
            for item in unknown_groups
        ],
        "temporal_windows": TEMPORAL_WINDOWS.get(dataset, {}),
        "classes": labels,
        "flow_count_by_split": {
            split: {
                label: int(counts[(group_split, label)])
                for group_split, label in sorted(counts)
                if group_split == split
            }
            for split in caps
        },
        "available_flow_count_by_split": {
            split: {
                label: int(available_by_label[(group_split, label)])
                for group_split, label in available_by_label
                if group_split == split
            }
            for split in caps
        },
        "target_flow_count_by_split": {
            split: {
                label: int(target_by_label[(group_split, label)])
                for group_split, label in target_by_label
                if group_split == split
            }
            for split in caps
        },
        "flow_count_by_source_group": {
            split: _counter_by_group(group_counts, split) for split in caps
        },
        "available_flow_count_by_source_group": {
            split: _counter_by_group(available, split) for split in caps
        },
        "target_flow_count_by_source_group": {
            split: _counter_by_group(target, split) for split in caps
        },
        "total_flows": int(sum(counts.values())),
        "packet_rows": int(packet_rows),
    }
    for key in (
        "known_apps",
        "unknown_apps",
        "unknown_candidate_pool",
        "unknown_candidate_pool_complete",
        "unknown_application_groups",
        "unknown_split_seed",
        "synthetic_noise",
    ):
        if key in source_metadata:
            report[key] = source_metadata[key]
    report_path = output_csv.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--dataset", choices=["tls", "quic"], required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="small")
    parser.add_argument("--seed", type=int, default=599)
    args = parser.parse_args()
    report = sample_dataset(args.input_csv, args.output_csv, args.dataset, args.profile, args.seed)
    print(json.dumps({"out_csv": report["out_csv"], "total_flows": report["total_flows"], "caps_per_class": report["caps_per_class"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
