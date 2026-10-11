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
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.sampler import append_synthetic_unknown


UNKNOWN_LABELS = {"unknown", "_unknown", "__unknown__"}
UNKNOWN_GROUP_COLUMNS = ("source_group", "original_app", "noise_family")


PROFILES = {
    # The profile name describes the known-class train budget. Validation and
    # test use the same per-class ratios; unknown rows have separate global budgets
    # below and are never allowed to multiply with the number of applications.
    "small": {"train": 200, "val": 40, "test": 40},
    "medium": {"train": 2000, "val": 400, "test": 400},
    "large": {"train": 20000, "val": 4000, "test": 4000},
}

NOISE_FAMILIES = {
    "train": "gaussian_iid_v1",
    "val": "shuffle_spike_v2",
    "test": "mixture_burst_v3",
}

# Final open-set data protocol: real applications outside the known pool are
# sampled at half the selected known-flow count, with an additional ten
# percent of deterministic synthetic noise.  These values are shared by every
# profile and are recorded in each manifest/report.
REAL_UNKNOWN_RATIO = 0.50
SYNTHETIC_NOISE_RATIO = 0.10

TEMPORAL_WINDOWS = {
    "tls": {
        "train": "W-2021-40 days 20211004-20211010 (7 days)",
        "val": "W-2021-41 day 20211011",
        "test": "W-2021-41 days 20211012-20211017 (6 days)",
    },
    "quic": {
        "train": "W-2022-44 days 20221031-20221106 (7 days)",
        "val": "W-2022-45 day 20221107",
        "test": "W-2022-45 days 20221108-20221113 (6 days)",
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


def _is_synthetic_unknown(group: tuple[str, str, str, str]) -> bool:
    """Return whether an unknown provenance group is generated noise.

    Exported synthetic rows carry at least one of these markers.  Keeping the
    check at group level lets the sampler enforce separate real-unknown and
    synthetic-noise budgets without inspecting packets again.
    """

    label, source_group, original_app, noise_family = group
    if label != "unknown":
        return False
    source_group = source_group.lower()
    original_app = original_app.lower()
    return bool(
        noise_family
        or source_group.startswith("noise_")
        or source_group == "synthetic"
        or original_app.startswith("synthetic_noise::")
    )


def _balanced_unknown_ids(
    groups: list[tuple[str, str, str, str]],
    candidates: dict[tuple[str, tuple[str, str, str, str]], list[tuple[int, str]]],
    split: str,
    budget: int,
) -> dict[tuple[str, tuple[str, str, str, str]], list[tuple[int, str]]]:
    """Select up to ``budget`` flows by round-robin over provenance groups.

    A round-robin pass gives each application/source group one flow before a
    second pass begins, so a prolific unknown application cannot consume the
    whole budget.  The deterministic rank order keeps repeated exports stable.
    """

    ordered_groups = sorted(groups, key=lambda group: _group_name(group))
    values = {
        group: sorted(candidates[(split, group)], key=lambda item: item[0])
        for group in ordered_groups
    }
    pointers = {group: 0 for group in ordered_groups}
    selected: dict[tuple[str, tuple[str, str, str, str]], list[tuple[int, str]]] = defaultdict(list)
    remaining = max(0, int(budget))
    while remaining and ordered_groups:
        made_progress = False
        for group in ordered_groups:
            pointer = pointers[group]
            if pointer >= len(values[group]):
                continue
            selected[(split, group)].append(values[group][pointer])
            pointers[group] = pointer + 1
            remaining -= 1
            made_progress = True
            if not remaining:
                break
        if not made_progress:
            break
    return selected


def _select_ids(input_csv: Path, caps: dict[str, int], seed: int):
    candidates: dict[tuple[str, tuple[str, str, str, str]], list[tuple[int, str]]] = defaultdict(list)
    with input_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        for flow_id, rows in _flow_rows(handle):
            first = rows[0]
            split = str(first["split"]).lower()
            group = _group_key(first)
            # Source exports created by the previous protocol already contain
            # synthetic noise.  It must not be sampled into a final profile:
            # final noise is generated after known/real-unknown selection so
            # its count is exactly the requested fraction of selected known
            # flows rather than the fraction available in the source file.
            if _is_synthetic_unknown(group):
                continue
            if split not in caps:
                continue
            candidates[(split, group)].append((_rank(seed, split, _group_name(group), flow_id), flow_id))

    selected: set[str] = set()
    available = Counter()
    target = Counter()
    manifest_groups = []
    selected_by_group: dict[tuple[str, tuple[str, str, str, str]], list[tuple[int, str]]] = defaultdict(list)

    # Known classes retain the profile cap independently.  These counts are
    # also the denominator for the two global unknown budgets.
    known_counts_by_split = Counter()
    for (split, group), values in sorted(candidates.items(), key=lambda item: (item[0][0], item[0][1])):
        if group[0] == "unknown":
            continue
        values.sort(key=lambda item: item[0])
        selected_values = values[: caps[split]]
        selected_by_group[(split, group)] = selected_values
        known_counts_by_split[split] += len(selected_values)

    # Unknown applications and generated noise receive separate budgets.  The
    # source groups are sampled round-robin so the budget is balanced by
    # original application/source identity rather than pooled by the label.
    budget_by_split = {}
    noise_budget_by_split = {}
    for split in caps:
        unknown_groups = [
            group
            for (group_split, group) in candidates
            if group_split == split and group[0] == "unknown" and not _is_synthetic_unknown(group)
        ]
        noise_groups = [
            group
            for (group_split, group) in candidates
            if group_split == split and group[0] == "unknown" and _is_synthetic_unknown(group)
        ]
        real_available = sum(len(candidates[(split, group)]) for group in unknown_groups)
        noise_available = sum(len(candidates[(split, group)]) for group in noise_groups)
        real_budget = min(int(round(known_counts_by_split[split] * REAL_UNKNOWN_RATIO)), real_available)
        noise_budget = min(int(round(known_counts_by_split[split] * SYNTHETIC_NOISE_RATIO)), noise_available)
        budget_by_split[split] = real_budget
        noise_budget_by_split[split] = noise_budget
        selected_by_group.update(_balanced_unknown_ids(unknown_groups, candidates, split, real_budget))
        selected_by_group.update(_balanced_unknown_ids(noise_groups, candidates, split, noise_budget))

    for (split, group), values in sorted(candidates.items(), key=lambda item: (item[0][0], item[0][1])):
        group_name = _group_name(group)
        available[(split, group)] = len(values)
        selected_values = selected_by_group.get((split, group), [])
        target[(split, group)] = len(selected_values)
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
                # isolation. Omitting known-class IDs keeps sampling manifests
                # compact while retaining deterministic counts for them.
                "selected_flow_ids": [flow_id for _, flow_id in selected_values]
                if group[0] == "unknown"
                else [],
            }
        )
    return selected, available, target, manifest_groups, dict(budget_by_split), dict(noise_budget_by_split)


def sample_dataset(
    input_csv: Path,
    output_csv: Path,
    dataset: str,
    profile: str,
    seed: int,
) -> dict:
    caps = PROFILES[profile]
    (
        selected,
        available,
        target,
        manifest_groups,
        unknown_budget_by_split,
        noise_budget_by_split,
    ) = _select_ids(input_csv, caps, seed)
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

    # Generate the final synthetic component only after known and real
    # unknown flows have been selected.  This removes legacy synthetic rows
    # from source exports and makes the 10% denominator auditable.
    noise_counts = append_synthetic_unknown(
        output_csv,
        seq_len=30,
        noise_ratio=SYNTHETIC_NOISE_RATIO,
        seed=seed,
    )
    for split, flow_count in noise_counts.items():
        counts[(split, "unknown")] += int(flow_count)
        noise_group = (
            "unknown",
            f"noise_{split}",
            f"synthetic_noise::{NOISE_FAMILIES[split]}",
            NOISE_FAMILIES[split],
        )
        group_counts[(split, noise_group)] += int(flow_count)
        packet_rows += int(flow_count) * 30

    # The source export contains no final synthetic rows after selection, so
    # the protocol budget must be reported from the selected known counts,
    # alongside the actual generated count.  Reporting the source candidate
    # count here would incorrectly show zero even when noise was generated.
    noise_budget_actual_by_split = {
        split: int(round(
            sum(
                counts[(split, label)]
                for (count_split, label) in counts
                if count_split == split and label != "unknown"
            ) * SYNTHETIC_NOISE_RATIO
        ))
        for split in caps
    }

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
        "known_class_caps": caps,
        "real_unknown_ratio": REAL_UNKNOWN_RATIO,
        "synthetic_noise_ratio": SYNTHETIC_NOISE_RATIO,
        "real_unknown_budget_by_split": unknown_budget_by_split,
        "synthetic_noise_budget_by_split": {
            split: noise_budget_actual_by_split[split]
            for split in caps
        },
        "synthetic_noise_actual_by_split": noise_counts,
        "synthetic_noise_families": dict(NOISE_FAMILIES),
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
        "known_class_caps": caps,
        "real_unknown_ratio": REAL_UNKNOWN_RATIO,
        "synthetic_noise_ratio": SYNTHETIC_NOISE_RATIO,
        "real_unknown_budget_by_split": unknown_budget_by_split,
        "synthetic_noise_budget_by_split": noise_budget_actual_by_split,
        "synthetic_noise_actual_by_split": noise_counts,
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
