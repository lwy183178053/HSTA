"""Create balanced, temporally ordered subsets from a processed S CSV.

The source exporter already assigns disjoint temporal windows to ``train``,
``val`` and ``test``. This utility samples complete flows within each
``(split, label)`` group, so no packet from a selected flow is split across
partitions and class balance is reproducible without loading the CSV into
memory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


PROFILES = {
    "tiny": {"train": 100, "val": 20, "test": 20},
    "small": {"train": 500, "val": 100, "test": 100},
    "medium": {"train": 1000, "val": 200, "test": 200},
    "paper": {"train": 10000, "val": 1000, "test": 2000},
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


def _select_ids(input_csv: Path, caps: dict[str, int], seed: int):
    candidates: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    with input_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        for flow_id, rows in _flow_rows(handle):
            first = rows[0]
            split = str(first["split"]).lower()
            label = str(first["label"])
            if split not in caps:
                continue
            candidates[(split, label)].append((_rank(seed, split, label, flow_id), flow_id))

    selected: set[str] = set()
    available = Counter()
    target = Counter()
    for (split, label), values in sorted(candidates.items()):
        values.sort(key=lambda item: item[0])
        available[(split, label)] = len(values)
        target[(split, label)] = min(caps[split], len(values))
        selected.update(flow_id for _, flow_id in values[: caps[split]])
    return selected, available, target


def sample_dataset(
    input_csv: Path,
    output_csv: Path,
    dataset: str,
    profile: str,
    seed: int,
) -> dict:
    caps = PROFILES[profile]
    selected, available, target = _select_ids(input_csv, caps, seed)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
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
            for row in rows:
                writer.writerow(row)
            counts[(split, label)] += 1

    labels = sorted({label for split, label in counts})
    report = {
        "source_csv": input_csv.as_posix(),
        "out_csv": output_csv.as_posix(),
        "dataset": dataset,
        "size": "S",
        "profile": profile,
        "selection_seed": int(seed),
        "sampling_unit": "complete_flow",
        "caps_per_class": caps,
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
                label: int(available[(group_split, label)])
                for group_split, label in available
                if group_split == split
            }
            for split in caps
        },
        "target_flow_count_by_split": {
            split: {
                label: int(target[(group_split, label)])
                for group_split, label in target
                if group_split == split
            }
            for split in caps
        },
        "total_flows": int(sum(counts.values())),
        "packet_rows": int(sum(counts.values()) * 30),
    }
    report_path = output_csv.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--dataset", choices=["tls", "quic"], required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="tiny")
    parser.add_argument("--seed", type=int, default=599)
    args = parser.parse_args()
    report = sample_dataset(args.input_csv, args.output_csv, args.dataset, args.profile, args.seed)
    print(json.dumps({"out_csv": report["out_csv"], "total_flows": report["total_flows"], "caps_per_class": report["caps_per_class"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
