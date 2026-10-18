from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from tqdm import tqdm

SERVICE_COLUMNS = {
    "Service": "traffic_name",
    "Service Provider": "service_provider",
    "Tag": "service_tag",
    "Service Category": "service_category",
    "Domains": "domains",
}
SPLITS = ("train", "val", "test")
CSV_FIELDS = (
    "flow_id", "label", "pkt_index", "size", "direction", "delta_time", "split", "source",
    "original_app", "source_group", "noise_family", "capture_date", "source_flow_id",
)


def _project_path(path: str | Path, project_root: str | Path) -> str:
    """Store portable project-relative paths in generated reports."""
    path = Path(path).resolve()
    root = Path(project_root).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _imports():
    from cesnet_datazoo.config import AppSelection, DatasetConfig, ValidationApproach, DataLoaderOrder
    from cesnet_datazoo.datasets import CESNET_QUIC22, CESNET_TLS22

    return CESNET_TLS22, CESNET_QUIC22, DatasetConfig, AppSelection, ValidationApproach, DataLoaderOrder


def select_available_top_apps(
    counts: Counter[str] | dict[str, int],
    available_classes: list[str] | set[str],
    topk: int,
) -> tuple[list[str], list[str]]:
    """Select observed top classes and keep every available non-background remainder."""
    available = {
        str(name) for name in available_classes
        if not str(name).endswith("-background")
    }
    ordered = [
        name for name, _ in sorted(
            ((name, count) for name, count in counts.items() if name in available),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    known = ordered[:int(topk)]
    unknown = sorted(available - set(known))
    return known, unknown


def global_training_top_apps(dataset_name: str, project_root: str | Path, size: str,
                             dates: list[str], topk: int = 60,
                             available_classes: list[str] | set[str] | None = None) -> tuple[list[str], list[str], dict[str, int]]:
    """Count training H5 APP IDs, restricted to the current DataZoo size classes."""
    if available_classes is None:
        raise ValueError("available_classes from the initialized DataZoo dataset is required")
    import tables
    CESNET_TLS22, CESNET_QUIC22, _, _, _, _ = _imports()
    cls = CESNET_TLS22 if dataset_name == "tls" else CESNET_QUIC22
    root = Path(project_root).resolve() / "data" / "raw" / (
        "cesnet_tls22_datazoo" if dataset_name == "tls" else "cesnet_quic22_datazoo"
    ) / size.upper()
    base_name = cls.database_filename
    stem, suffix = os.path.splitext(base_name)
    h5_path = root / f"{stem}-{size.upper()}{suffix}"
    enum = {int(k): str(v) for k, v in cls._tables_app_enum.items()}
    counts: Counter[str] = Counter()
    with tables.open_file(str(h5_path), mode="r") as database:
        for date in dates:
            table = database.get_node(f"/flows/D{date}")
            values = np.asarray(table.col("APP"), dtype=np.int64)
            for app_id, count in zip(*np.unique(values, return_counts=True)):
                name = enum.get(int(app_id), str(app_id))
                if not str(name).endswith("-background"):
                    counts[name] += int(count)
    known, unknown = select_available_top_apps(counts, available_classes, topk)
    return known, unknown, dict(counts)


# The dates are disjoint and ordered.  The first complete week is used for
# training, then the first day of the following week is validation and the
# remaining six days are test.  This gives training the full first-week
# history while keeping validation and test strictly forward-looking.
TEMPORAL_DATE_SPLITS = {
    "tls": {
        "train": ["20211004", "20211005", "20211006", "20211007", "20211008", "20211009", "20211010"],
        "val": ["20211011"],
        "test": ["20211012", "20211013", "20211014", "20211015", "20211016", "20211017"],
    },
    "quic": {
        "train": [f"202210{day:02d}" for day in range(31, 32)] + [f"202211{day:02d}" for day in range(1, 14)],
        "val": ["20221114", "20221115"],
        "test": [f"202211{day:02d}" for day in range(16, 28)],
    },
}
UNKNOWN_LABEL = "unknown"
PPI_LEN = 30
UNKNOWN_SOURCE_GROUPS = ("unknown_support", "unknown_val_heldout", "unknown_test_heldout")
DEFAULT_NOISE_FAMILIES = {
    # These names are part of the data audit protocol.  Each split uses a
    # different generator family; parameters are estimated from train rows.
    "train": "gaussian_iid_v1",
    "val": "shuffle_spike_v2",
    "test": "mixture_burst_v3",
}


def resolve_datazoo_workers(workers: int | str | None) -> int:
    """Resolve the DataZoo loader worker setting.

    HDF5 reads are CPU-bound, but an unbounded process count often makes the
    shared source disk slower and can duplicate large buffers.  ``auto``
    therefore uses all but one logical CPU up to a conservative configurable
    cap.  An explicit integer remains unchanged for reproducible runs.
    """
    if workers is None:
        return 0
    if isinstance(workers, str):
        value = workers.strip().lower()
        if value == "auto":
            cpu_count = os.cpu_count() or 1
            try:
                cap = int(os.environ.get("HSTA_MAX_DATAZOO_WORKERS", "8"))
            except ValueError:
                cap = 8
            cap = max(1, cap)
            return max(1, min(max(1, cpu_count - 1), cap))
        workers = int(value)
    workers = int(workers)
    if workers < 0:
        raise ValueError("datazoo workers must be >= 0 or 'auto'")
    return workers


def _to_np(x):
    try:
        import torch

        if isinstance(x, torch.Tensor):
            return x.detach().cpu().numpy()
    except Exception:
        pass
    return x if isinstance(x, np.ndarray) else np.asarray(x)


def _scalar_str(x) -> str:
    a = _to_np(x)
    if a.shape == ():
        return str(a.item())
    if a.size == 1:
        return str(a.reshape(-1)[0].item())
    return str(a.tolist())


def decode_label(x, dataset=None) -> str:
    value = _scalar_str(x)
    try:
        index = int(float(value))
    except Exception:
        return value
    # DataZoo stores encoded labels in the fourth batch field.  Its encoder
    # lives under class_info rather than on the dataset object itself.
    class_info = getattr(dataset, "class_info", None)
    if class_info is not None:
        unknown_index = getattr(class_info, "unknown_class_label", None)
        target_names = getattr(class_info, "target_names", None)
        if unknown_index is not None and index == int(unknown_index):
            return UNKNOWN_LABEL
        if target_names is not None and 0 <= index < len(target_names):
            return str(target_names[index])
    for attr in [
        "label_to_name",
        "idx_to_label",
        "idx_to_app",
        "label_encoder",
        "classes",
        "classes_",
        "app_names",
        "apps",
        "apps_list",
    ]:
        if not hasattr(dataset, attr):
            continue
        obj = getattr(dataset, attr)
        try:
            if isinstance(obj, dict):
                return str(obj.get(index, obj.get(str(index), value)))
            if isinstance(obj, (list, tuple)) and 0 <= index < len(obj):
                return str(obj[index])
            if hasattr(obj, "inverse_transform"):
                return str(obj.inverse_transform([index])[0])
        except Exception:
            continue
    return value


def _infer_dataset_name(csv_path: str | Path | None = None, report: dict | None = None) -> str | None:
    if report and report.get("dataset"):
        return str(report["dataset"]).lower()
    if csv_path is None:
        return None
    name = Path(csv_path).name.lower()
    if "tls" in name:
        return "tls"
    if "quic" in name:
        return "quic"
    return None


def _infer_size(csv_path: str | Path | None = None, report: dict | None = None) -> str:
    if report and report.get("size"):
        return str(report["size"]).upper()
    if csv_path is not None:
        stem = Path(csv_path).stem.lower()
        for size in ("xs", "s", "m", "l"):
            if f"_{size}_" in stem:
                return size.upper()
    return "S"


def infer_servicemap_path(
    dataset_name: str | None,
    size: str = "S",
    project_root: str | Path = ".",
) -> Path | None:
    if dataset_name not in {"tls", "quic"}:
        return None
    root = Path(project_root).resolve()
    dataset_dir = "cesnet_tls22_datazoo" if dataset_name == "tls" else "cesnet_quic22_datazoo"
    candidate = root / "data" / "raw" / dataset_dir / size.upper() / "servicemap.csv"
    if candidate.exists():
        return candidate
    fallback = root / "data" / "raw" / dataset_dir / "S" / "servicemap.csv"
    if fallback.exists():
        return fallback
    return None


def load_servicemap(servicemap_path: str | Path | None) -> dict[int, dict]:
    if servicemap_path is None:
        return {}
    servicemap_path = Path(servicemap_path)
    if not servicemap_path.exists():
        return {}
    mapping = {}
    with servicemap_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            mapping[int(index)] = {
                output_col: str(row.get(input_col, "") or "")
                for input_col, output_col in SERVICE_COLUMNS.items()
            }
    return mapping


def service_info(datazoo_label: str, service_by_id: dict[int, dict]) -> dict:
    try:
        service_id = int(float(datazoo_label))
    except ValueError:
        service_id = None
    if service_id is None or service_id not in service_by_id:
        return {
            "traffic_name": datazoo_label,
            "service_provider": "",
            "service_tag": "",
            "service_category": "",
            "domains": "",
        }
    return dict(service_by_id[service_id])


def _sorted_labels(labels) -> list[str]:
    return sorted({str(label) for label in labels})


def partition_unknown_apps(
    applications: list[str] | tuple[str, ...] | set[str],
    seed: int = 599,
    support_fraction: float = 0.5,
    val_fraction: float = 0.25,
) -> dict[str, list[str]]:
    """Split unknown application identities before they are label-folded.

    The split is deterministic, identity-disjoint, and independent of flow
    sampling.  ``support`` applications are the only real unknown identities
    eligible for MVIF-Net open-set training; validation and test identities are
    held out from training entirely.  A small candidate pool is handled by
    assigning at least one application to each non-empty group when possible.
    """
    apps = sorted({str(app) for app in applications if str(app) and str(app) != UNKNOWN_LABEL})
    if not apps:
        return {key: [] for key in UNKNOWN_SOURCE_GROUPS}
    if not 0 < support_fraction < 1 or not 0 <= val_fraction < 1 or support_fraction + val_fraction >= 1:
        raise ValueError("support_fraction and val_fraction must leave a non-empty test fraction")
    rng = np.random.default_rng(int(seed))
    order = rng.permutation(len(apps))
    shuffled = [apps[int(index)] for index in order]
    n = len(shuffled)
    if n >= 3:
        support_n = max(1, int(round(n * support_fraction)))
        val_n = max(1, int(round(n * val_fraction)))
        if support_n + val_n >= n:
            val_n = max(1, n - support_n - 1)
        test_n = n - support_n - val_n
        if test_n < 1:
            test_n = 1
            if support_n > 1:
                support_n -= 1
            else:
                val_n -= 1
    elif n == 2:
        support_n, val_n, test_n = 1, 0, 1
    else:
        support_n, val_n, test_n = 1, 0, 0
    return {
        "unknown_support": sorted(shuffled[:support_n]),
        "unknown_val_heldout": sorted(shuffled[support_n : support_n + val_n]),
        "unknown_test_heldout": sorted(shuffled[support_n + val_n : support_n + val_n + test_n]),
    }


def unknown_application_source_map(groups: dict[str, list[str]]) -> dict[str, str]:
    """Return ``original_app -> source_group`` for exported flow metadata."""
    mapping: dict[str, str] = {}
    for source_group, applications in groups.items():
        for application in applications:
            application = str(application)
            if application in mapping:
                raise ValueError(f"unknown application appears in multiple groups: {application}")
            mapping[application] = str(source_group)
    return mapping


def _counter_dict(counter: Counter) -> dict[str, int]:
    return {str(key): int(counter[key]) for key in sorted(counter)}


def _selection_ranking(dataset, selected_apps: list[str]) -> list[dict]:
    """Return the train-count audit rows exposed by DataZoo after selection.

    DataZoo applies the frequency sort and provider-group constraint internally.
    ``known_app_counts`` contains the post-selection counts, so these rows are
    intentionally labelled as the selected-set audit rather than a claim that
    they are a strict global top-k ranking.
    """
    counts = getattr(dataset, "known_app_counts", None)
    train_counts: dict[str, int] = {}
    try:
        if counts is not None and "Train" in counts.columns:
            train_counts = {str(name): int(value) for name, value in counts["Train"].items()}
    except Exception:
        train_counts = {}
    ordered = sorted(
        (str(app) for app in selected_apps),
        key=lambda app: (-train_counts.get(app, 0), app),
    )
    return [
        {
            "selected_rank": int(rank),
            "application": app,
            "train_flow_count": int(train_counts.get(app, 0)),
        }
        for rank, app in enumerate(ordered, start=1)
    ]


def _split_counter_dict(split_counters: dict[str, Counter]) -> dict[str, dict[str, int]]:
    return {split: _counter_dict(split_counters.get(split, Counter())) for split in sorted(split_counters)}


def _count_stats(values: list[int]) -> dict:
    if not values:
        return {"min": 0, "max": 0, "mean": 0.0, "median": 0.0, "balanced": True}
    ordered = sorted(int(value) for value in values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        median = float(ordered[mid])
    else:
        median = float((ordered[mid - 1] + ordered[mid]) / 2)
    return {
        "min": int(ordered[0]),
        "max": int(ordered[-1]),
        "mean": float(sum(ordered) / len(ordered)),
        "median": median,
        "balanced": bool(ordered[0] == ordered[-1]),
    }


def build_class_report(
    labels,
    flow_count_by_split: dict[str, Counter],
    packet_row_count_by_split: dict[str, Counter] | None = None,
    service_by_id: dict[int, dict] | None = None,
) -> tuple[list[dict], dict]:
    service_by_id = service_by_id or {}
    packet_row_count_by_split = packet_row_count_by_split or {}
    label_list = _sorted_labels(labels)
    rows = []
    for model_label_id, label in enumerate(label_list):
        flow_count = sum(int(flow_count_by_split.get(split, Counter()).get(label, 0)) for split in flow_count_by_split)
        packet_row_count = sum(
            int(packet_row_count_by_split.get(split, Counter()).get(label, 0))
            for split in packet_row_count_by_split
        )
        row = {
            "model_label_id": int(model_label_id),
            "datazoo_label": label,
            **service_info(label, service_by_id),
            "flow_count": int(flow_count),
            "packet_row_count": int(packet_row_count),
        }
        for split in SPLITS:
            row[f"{split}_flow_count"] = int(flow_count_by_split.get(split, Counter()).get(label, 0))
            row[f"{split}_packet_row_count"] = int(packet_row_count_by_split.get(split, Counter()).get(label, 0))
        rows.append(row)

    summary = {
        "num_classes": int(len(rows)),
        "total_flows": int(sum(row["flow_count"] for row in rows)),
        "total_packet_rows": int(sum(row["packet_row_count"] for row in rows)),
        "flow_count": _count_stats([row["flow_count"] for row in rows]),
        "packet_row_count": _count_stats([row["packet_row_count"] for row in rows]),
    }
    for split in SPLITS:
        summary[f"{split}_flow_count"] = _count_stats([row[f"{split}_flow_count"] for row in rows])
        summary[f"{split}_packet_row_count"] = _count_stats([row[f"{split}_packet_row_count"] for row in rows])
    return rows, summary


def scan_processed_csv_counts(
    csv_path: str | Path,
    label_col: str = "label",
    flow_col: str = "flow_id",
    split_col: str = "split",
) -> dict:
    labels = set()
    row_counts_by_split = defaultdict(Counter)
    flow_counts_by_split = defaultdict(Counter)
    seen_flows = set()
    total_rows = 0

    with Path(csv_path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if label_col not in (reader.fieldnames or []):
            raise ValueError(f"{csv_path} does not contain label column: {label_col}")
        has_flow = flow_col in (reader.fieldnames or [])
        has_split = split_col in (reader.fieldnames or [])
        has_packet_index = "pkt_index" in (reader.fieldnames or [])

        for row_index, row in enumerate(reader):
            label = str(row.get(label_col, "") or "")
            if not label:
                continue
            split = str(row.get(split_col, "all") if has_split else "all").lower()
            labels.add(label)
            row_counts_by_split[split][label] += 1
            total_rows += 1

            # Every exported flow has exactly one pkt_index=0 row.  Counting
            # that row avoids retaining millions of flow IDs in memory while
            # scanning the package-level CSV.  Keep the set fallback for
            # legacy files without packet indices.
            if has_packet_index and str(row.get("pkt_index", "")) != "0":
                continue
            flow_id = str(row.get(flow_col, row_index) if has_flow else row_index)
            if not has_packet_index:
                if flow_id in seen_flows:
                    continue
                seen_flows.add(flow_id)
            flow_counts_by_split[split][label] += 1

    return {
        "labels": _sorted_labels(labels),
        "flow_count_by_split": dict(flow_counts_by_split),
        "packet_row_count_by_split": dict(row_counts_by_split),
        "packet_rows": int(total_rows),
    }


def scan_processed_source_counts(csv_path: str | Path) -> dict[str, dict[str, Counter]]:
    """Count complete flows by split and preserved source metadata."""
    source_counts: dict[str, Counter] = defaultdict(Counter)
    app_counts: dict[str, Counter] = defaultdict(Counter)
    seen: set[str] = set()
    with Path(csv_path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        has_packet_index = "pkt_index" in (reader.fieldnames or [])
        for row in reader:
            if has_packet_index and str(row.get("pkt_index", "")) != "0":
                continue
            flow_id = str(row.get("flow_id", ""))
            if not has_packet_index:
                if not flow_id or flow_id in seen:
                    continue
                seen.add(flow_id)
            split = str(row.get("split", "all")).lower()
            source_group = str(row.get("source_group", row.get("source", "")) or "")
            original_app = str(row.get("original_app", "") or "")
            source_counts[split][source_group] += 1
            app_counts[split][original_app] += 1
    return {"source_group": dict(source_counts), "original_app": dict(app_counts)}


def enrich_processed_report(
    csv_path: str | Path,
    report_path: str | Path | None = None,
    project_root: str | Path = ".",
) -> dict:
    csv_path = Path(csv_path)
    if report_path is None:
        report_path = csv_path.with_suffix(".report.json")
    report_path = Path(report_path)

    report = {}
    if report_path.exists():
        with report_path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)

    dataset_name = _infer_dataset_name(csv_path, report)
    size = _infer_size(csv_path, report)
    dataset_root = Path(project_root).resolve() / "data" / "raw" / (
        "cesnet_tls22_datazoo" if dataset_name == "tls" else "cesnet_quic22_datazoo"
    )
    counts = scan_processed_csv_counts(csv_path)
    servicemap_path = infer_servicemap_path(dataset_name, size=size, project_root=project_root)
    service_by_id = load_servicemap(servicemap_path)
    class_summary, class_count_summary = build_class_report(
        counts["labels"],
        counts["flow_count_by_split"],
        counts["packet_row_count_by_split"],
        service_by_id=service_by_id,
    )

    report.update(
        {
            "dataset": dataset_name or report.get("dataset", ""),
            "size": size,
            "dataset_root": _project_path(dataset_root, project_root),
            "out_csv": _project_path(csv_path, project_root),
            "servicemap_path": _project_path(servicemap_path, project_root) if servicemap_path else "",
            "flow_count_by_split": _split_counter_dict(counts["flow_count_by_split"]),
            "packet_row_count_by_split": _split_counter_dict(counts["packet_row_count_by_split"]),
            "packet_rows": counts["packet_rows"],
            "class_summary": class_summary,
            "class_count_summary": class_count_summary,
        }
    )
    report.setdefault("classes", counts["labels"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


def build_dataset(
    name: str,
    size: str,
    project_root: str | Path,
    train_size: int | str = 500000,
    val_size: int | str = 200000,
    test_size: int | str = 200000,
    batch_size: int = 64,
    test_batch_size: int = 64,
    workers: int = 0,
    known_topk: int | None = 60,
    unknown_count: int | None = None,
    unknown_split_seed: int = 599,
    temporal_split: bool = True,
):
    CESNET_TLS22, CESNET_QUIC22, DatasetConfig, AppSelection, ValidationApproach, DataLoaderOrder = _imports()
    workers = resolve_datazoo_workers(workers)
    root = Path(project_root).resolve()
    size = size.upper()
    if name == "tls":
        dataset_root = root / "data" / "raw" / "cesnet_tls22_datazoo"
        dataset_cls = CESNET_TLS22
    elif name == "quic":
        dataset_root = root / "data" / "raw" / "cesnet_quic22_datazoo"
        dataset_cls = CESNET_QUIC22
    else:
        raise ValueError(f"Unknown dataset: {name}")

    dataset = dataset_cls(str(dataset_root), size=size)
    dates = TEMPORAL_DATE_SPLITS[name]
    train_dates = dates["train"] if temporal_split else []
    val_dates = dates["val"] if temporal_split else []
    test_dates = dates["test"] if temporal_split else []
    # DataZoo exposes one train week and one immediately following test week.
    # Use the complete first week for training, then reserve the first day of
    # the following week for validation and the remaining six days for test.
    # The three windows are disjoint and strictly ordered.
    train_period = dataset.default_train_period_name
    test_period = dataset.default_test_period_name

    def config_for(dataset, selection, **selection_kwargs):
        common = dict(
            dataset=dataset,
            apps_selection=selection,
            train_period_name=train_period,
            # Validation now lives on the first day of the following period,
            # alongside the explicit forward test dates below.  Keeping the
            # period name aligned makes DataZoo caches and reports auditable.
            val_period_name=test_period if temporal_split else "",
            test_period_name=test_period,
            train_dates=train_dates,
            val_dates=val_dates,
            test_dates=test_dates,
            val_approach=ValidationApproach.VALIDATION_DATES if temporal_split else ValidationApproach.SPLIT_FROM_TRAIN,
            train_size=train_size,
            val_known_size=val_size,
            test_known_size=test_size,
            # DataZoo emits these as the open-world class.  We retain them in
            # val/test and add a small synthetic unknown set during export.
            val_unknown_size=val_size,
            test_unknown_size=test_size,
            batch_size=batch_size,
            test_batch_size=test_batch_size,
            train_workers=workers,
            val_workers=workers,
            test_workers=workers,
            # Keep both index construction and the train dataloader order
            # deterministic for the formal protocol.
            random_state=599,
            train_dataloader_seed=599,
            train_dataloader_order=DataLoaderOrder.SEQUENTIAL,
            # Keep application names in the batch labels.  Folding to the
            # DataZoo unknown index here would make identity-level isolation
            # impossible to audit during CSV export.
            disable_label_encoding=True,
            **selection_kwargs,
        )
        if not temporal_split:
            common.pop("train_dates")
            common.pop("val_dates")
            common.pop("test_dates")
        return DatasetConfig(**common)

    # Select a true global top-k from all training-date H5 rows. DataZoo's
    # TOPX_KNOWN applies provider-group expansion, so it is not used here.
    selection_ranking: list[dict] = []
    if known_topk:
        global_known, global_unknown, global_counts = global_training_top_apps(
            name, root, size, train_dates, int(known_topk), dataset.available_classes
        )
        selection_ranking = [{"application": app, "count": global_counts.get(app, 0)}
                             for app in global_known]
        known_apps = global_known
        all_unknown_apps = global_unknown
        unknown_apps = all_unknown_apps if unknown_count is None else all_unknown_apps[:int(unknown_count)]
        unknown_groups = partition_unknown_apps(unknown_apps, seed=unknown_split_seed)
        train_support_apps = list(unknown_groups["unknown_support"])
        eval_unknown_apps = [app for group in ("unknown_val_heldout", "unknown_test_heldout") for app in unknown_groups[group]]
        dataset = dataset_cls(str(dataset_root), size=size)
        cfg = config_for(dataset, AppSelection.FIXED,
                         apps_selection_fixed_known=known_apps + train_support_apps,
                         apps_selection_fixed_unknown=eval_unknown_apps)
        candidate_pool_complete = unknown_count is None
        dataset._hsta_global_topk = True
        dataset._hsta_selection_ranking = selection_ranking
        dataset._hsta_global_counts = global_counts
    elif unknown_count is not None:
        probe_cfg = config_for(dataset, AppSelection.TOPX_KNOWN, apps_selection_topx=int(known_topk))
        dataset.set_dataset_config_and_initialize(probe_cfg, disable_indices_cache=True)
        known_apps = [str(x) for x in dataset.class_info.known_apps]
        all_unknown_apps = [str(x) for x in dataset.class_info.unknown_apps]
        selection_ranking = _selection_ranking(dataset, known_apps)
        unknown_apps = all_unknown_apps[: int(unknown_count)]
        if unknown_count > 0 and not unknown_apps:
            raise RuntimeError(f"No unknown applications available for {name} {size}")
        # Recreate the object so the generated index cache reflects the final
        # fixed known/unknown class list rather than the probe configuration.
        dataset = dataset_cls(str(dataset_root), size=size)
        unknown_groups = partition_unknown_apps(unknown_apps, seed=unknown_split_seed)
        train_support_apps = list(unknown_groups["unknown_support"])
        eval_unknown_apps = [
            app for group in ("unknown_val_heldout", "unknown_test_heldout")
            for app in unknown_groups[group]
        ]
        cfg = config_for(
            dataset,
            AppSelection.FIXED,
            # DataZoo's train loader exposes only ``known`` indices. Include
            # support applications in that index set, then fold them to the
            # explicit unknown label during export.
            apps_selection_fixed_known=known_apps + train_support_apps,
            apps_selection_fixed_unknown=eval_unknown_apps,
        )
        candidate_pool_complete = False
    else:
        cfg = config_for(dataset, AppSelection.ALL_KNOWN)
        known_apps = []
        unknown_apps = []
        unknown_groups = {key: [] for key in UNKNOWN_SOURCE_GROUPS}
        candidate_pool_complete = True
    # Keep protocol exports from writing additional DataZoo index caches. The
    # configuration hash still isolates any existing generated cache.
    dataset.set_dataset_config_and_initialize(cfg, disable_indices_cache=True)
    _include_validation_unknowns(dataset)
    # The validation repair replaces val.indices, so shuffle only afterwards.
    permute_split_indices(dataset, seed=599)
    # Keep the audit information attached to the object so export code does
    # not have to infer identities from the folded model labels.
    dataset._hsta_known_apps = list(known_apps or getattr(dataset.class_info, "known_apps", []))
    dataset._hsta_unknown_apps = list(unknown_apps or getattr(dataset.class_info, "unknown_apps", []))
    dataset._hsta_unknown_groups = unknown_groups
    dataset._hsta_unknown_source_map = unknown_application_source_map(unknown_groups)
    dataset._hsta_unknown_pool_complete = bool(candidate_pool_complete)
    dataset._hsta_selection_ranking = selection_ranking
    dataset._hsta_source_records = {split: source_records_for_dataset(dataset, split) for split in SPLITS}
    dataset._hsta_source_cursor = {split: 0 for split in SPLITS}
    return dataset, dataset_root


def _include_validation_unknowns(dataset) -> int:
    """Add DataZoo's validation unknown indices to its validation dataset.

    CESNET-DataZoo exposes ``val_unknown_indices`` in ``dataset_indices`` but
    currently constructs ``val_dataset`` from ``val_known_indices`` only. The
    formal open-set export must include both portions. We update only the
    already-initialized PyTablesDataset index array, preserving DataZoo's
    transforms, scaler, and label behavior.
    """
    val_dataset = getattr(dataset, "val_dataset", None)
    dataset_indices = getattr(dataset, "dataset_indices", None)
    if val_dataset is None or dataset_indices is None:
        return 0
    known = getattr(dataset_indices, "val_known_indices", None)
    unknown = getattr(dataset_indices, "val_unknown_indices", None)
    if known is None or unknown is None:
        return 0
    if len(unknown) == 0:
        return 0
    from numpy.lib.recfunctions import repack_fields
    from cesnet_datazoo.constants import INDICES_INDEX_FIELD, INDICES_TABLE_FIELD

    combined = np.concatenate((known, unknown))
    val_dataset.indices = repack_fields(combined[[INDICES_TABLE_FIELD, INDICES_INDEX_FIELD]])
    # The loader is normally created lazily; clear it defensively if a caller
    # requested it before this repair was applied.
    if hasattr(dataset, "val_dataloader"):
        dataset.val_dataloader = None
    dataset._hsta_val_includes_unknown = True
    return int(len(unknown))


def get_loader(dataset, split: str):
    if split == "train":
        return dataset.get_train_dataloader()
    if split == "val":
        return dataset.get_val_dataloader()
    if split == "test":
        return dataset.get_test_dataloader()
    raise ValueError(split)


class _SourceRecords:
    def __init__(self, subset):
        self.subset = subset
        self.paths = list(getattr(subset, "tables_paths", []))
    def __len__(self):
        return len(self.subset.indices)
    def __getitem__(self, index):
        item = self.subset.indices[index]
        names = item.dtype.names if hasattr(item, "dtype") else None
        table_id = int(item["TABLE"] if names else item[0])
        row_id = int(item["INDEX"] if names else item[1])
        table_path = self.paths[table_id]
        date = str(table_path).split("/flows/D")[-1]
        return date, f"{table_path}::row_{row_id}"


def source_records_for_dataset(dataset, split: str):
    """Map sequential DataZoo indices to real H5 date-table and row IDs."""
    subset = getattr(dataset, f"{split}_dataset", None)
    if subset is None or not hasattr(subset, "indices"):
        return []
    return _SourceRecords(subset)


def permute_split_indices(dataset, seed: int = 599) -> None:
    """Shuffle each split once while preserving ordinal source-ID mapping."""
    for offset, split in enumerate(SPLITS):
        subset = getattr(dataset, f"{split}_dataset", None)
        if subset is None or not hasattr(subset, "indices") or len(subset.indices) < 2:
            continue
        rng = np.random.default_rng(int(seed) + offset)
        subset.indices = subset.indices[rng.permutation(len(subset.indices))]
        if hasattr(dataset, f"{split}_dataloader"):
            setattr(dataset, f"{split}_dataloader", None)


def iter_batch(batch):
    if not isinstance(batch, (list, tuple)) or len(batch) < 4:
        raise RuntimeError(f"Unknown batch format: {type(batch)}")
    ppi = _to_np(batch[1])
    labels = _to_np(batch[3])
    if ppi.ndim == 0:
        ppi = ppi.reshape(1)
    batch_size = ppi.shape[0]
    for index in range(batch_size):
        label = labels if labels.shape == () else labels[index]
        yield ppi[index], label


def parse_ppi(ppi_one, seq_len: int):
    arr = np.squeeze(_to_np(ppi_one))
    if arr.ndim == 1:
        flat = arr.reshape(-1)
        if flat.size >= 3 * seq_len:
            x = flat[: 3 * seq_len].reshape(3, seq_len)
            times, dirs, sizes = x[0], x[1], x[2]
        elif flat.size >= 3:
            n = min(seq_len, flat.size // 3)
            x = flat[: 3 * n].reshape(n, 3)
            times, dirs, sizes = x[:, 0], x[:, 1], x[:, 2]
        else:
            times = np.zeros(1)
            dirs = np.ones(1)
            sizes = flat[:1]
    elif arr.ndim >= 2:
        if arr.shape[-1] >= 3 and arr.shape[0] != 3:
            times, dirs, sizes = arr[:seq_len, 0], arr[:seq_len, 1], arr[:seq_len, 2]
        elif arr.shape[0] >= 3:
            times, dirs, sizes = arr[0, :seq_len], arr[1, :seq_len], arr[2, :seq_len]
        elif arr.shape[-1] >= 3:
            times, dirs, sizes = arr[:seq_len, 0], arr[:seq_len, 1], arr[:seq_len, 2]
        else:
            return parse_ppi(arr.reshape(-1), seq_len)
    else:
        times = np.zeros(1)
        dirs = np.ones(1)
        sizes = np.zeros(1)

    times = np.asarray(times, dtype=np.float32).reshape(-1)[:seq_len]
    dirs = np.asarray(dirs, dtype=np.float32).reshape(-1)[:seq_len]
    sizes = np.asarray(sizes, dtype=np.float32).reshape(-1)[:seq_len]
    n = min(len(times), len(dirs), len(sizes), seq_len)
    return times[:n], dirs[:n], sizes[:n]


def scan_classes(dataset, topk: int = 8, scan_batches: int = 300):
    counts = Counter()
    for batch_index, batch in enumerate(tqdm(get_loader(dataset, "train"), desc="scan train labels")):
        for _, label in iter_batch(batch):
            counts[decode_label(label, dataset)] += 1
        if scan_batches and batch_index + 1 >= scan_batches:
            break
    return [label for label, _ in counts.most_common(topk)], counts


def export_csv(
    dataset,
    out_csv: str | Path,
    classes: list[str],
    seq_len: int,
    max_per_class_by_split: dict[str, int | None] | None = None,
    include_unknown: bool = True,
    unknown_source_labels: set[str] | None = None,
    unknown_source_groups: dict[str, list[str]] | None = None,
    max_batches_per_split: int | None = None,
):
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    selected = set(classes)
    unknown_source_labels = {str(label) for label in (unknown_source_labels or set())}
    source_map = unknown_application_source_map(unknown_source_groups or {})
    # Preserve compatibility with callers that only provide a set: those
    # identities are treated as test-heldout applications.
    source_map.update({label: "unknown_test_heldout" for label in unknown_source_labels if label not in source_map})
    selected.update(source_map)
    if include_unknown:
        selected.add(UNKNOWN_LABEL)
    split_counts = {split: Counter() for split in ["train", "val", "test"]}
    source_counts = {split: Counter() for split in ["train", "val", "test"]}
    packet_row_counts = {split: Counter() for split in ["train", "val", "test"]}
    split_caps = {"train": None, "val": None, "test": None}
    split_caps.update(max_per_class_by_split or {})
    packet_rows = 0
    with out_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        # The hot path writes one row per packet.  ``DictWriter.writerow``
        # performs a Python dict lookup for every field and becomes dominant
        # for large exports.  Keep the stable schema, but pass tuples to the
        # C csv writer and flush one batch at a time.
        writer = csv.writer(handle)
        writer.writerow(CSV_FIELDS)
        for split in ["train", "val", "test"]:
            split_cap = split_caps.get(split)
            flow_index = 0
            for batch_index, batch in enumerate(tqdm(get_loader(dataset, split), desc=f"export {split}")):
                output_rows = []
                for ppi_one, label_raw in iter_batch(batch):
                    source_records = getattr(dataset, "_hsta_source_records", {}).get(split, [])
                    cursor = getattr(dataset, "_hsta_source_cursor", {}).get(split, 0)
                    data_name = str(getattr(dataset, "name", "datazoo")).lower()
                    date_key = "quic" if "quic" in data_name else "tls"
                    if cursor < len(source_records):
                        capture_date, source_flow_id = source_records[cursor]
                    else:
                        capture_date = ""
                        source_flow_id = ""
                    if hasattr(dataset, "_hsta_source_cursor"):
                        dataset._hsta_source_cursor[split] = cursor + 1
                    original_app = decode_label(label_raw, dataset)
                    source_group = "known"
                    if original_app in source_map:
                        source_group = source_map[original_app]
                        # Real unknown applications are assigned to exactly
                        # one temporal role before label folding.  This keeps
                        # train support and test held-out identities disjoint.
                        expected_group = {
                            "train": "unknown_support",
                            "val": "unknown_val_heldout",
                            "test": "unknown_test_heldout",
                        }[split]
                        if source_group != expected_group:
                            continue
                        label = UNKNOWN_LABEL
                    else:
                        label = original_app
                    if label not in selected:
                        continue
                    source_key = (source_group, original_app) if label == UNKNOWN_LABEL else ("known", label)
                    source_cap = split_cap
                    # Real unknown applications are exported in full. Their
                    # The 50% real-unknown budget is applied later by the temporal sampler,
                    # with source-group round-robin balancing; applying a
                    # per-application cap here could make that budget
                    # impossible to satisfy.
                    if label == UNKNOWN_LABEL:
                        source_cap = None
                    if source_cap and source_counts[split][source_key] >= source_cap:
                        continue
                    times, dirs, sizes = parse_ppi(ppi_one, seq_len)
                    if len(sizes) == 0:
                        continue
                    flow_id = f"{split}_{flow_index}"
                    # In-memory DataZoo batches expose the source row only via
                    # indices. Keep a deterministic fallback until direct
                    # index metadata is attached by the dataset adapter.
                    if not source_flow_id and not hasattr(dataset, "_hsta_source_records"):
                        source_flow_id = f"test_fixture::{split}::{flow_index}"
                        capture_date = ""
                    if not source_flow_id:
                        raise RuntimeError(f"missing real H5 source index for {split} ordinal {cursor}")
                    flow_index += 1
                    split_counts[split][label] += 1
                    source_counts[split][source_key] += 1
                    for pkt_index in range(min(seq_len, len(sizes))):
                        output_rows.append(
                            (
                                flow_id,
                                label,
                                pkt_index,
                                float(sizes[pkt_index]),
                                float(dirs[pkt_index]) if pkt_index < len(dirs) else 1.0,
                                float(times[pkt_index]) if pkt_index < len(times) else 0.0,
                                split,
                                "datazoo",
                                original_app,
                                source_group,
                                "",
                                capture_date,
                                source_flow_id,
                            )
                        )
                        packet_rows += 1
                        packet_row_counts[split][label] += 1
                if output_rows:
                    writer.writerows(output_rows)
                expected_unknown = {
                    (group, app)
                    for app, group in source_map.items()
                    if group == {
                        "train": "unknown_support",
                        "val": "unknown_val_heldout",
                        "test": "unknown_test_heldout",
                    }[split]
                }
                known_keys = {("known", label) for label in classes}
                known_ready = bool(split_cap) and all(
                    source_counts[split][key] >= int(split_cap) for key in known_keys
                )
                # When real unknown applications are configured, they may be
                # ordered after all known flows in DataZoo's loader. Continue
                # scanning that split so held-out applications are actually
                # exported; the candidate list alone is not enough for a
                # valid open-set test file.
                if split_cap and known_ready and not expected_unknown:
                    break
                if max_batches_per_split and batch_index + 1 >= max_batches_per_split:
                    break
    return split_counts, packet_rows, packet_row_counts


def append_synthetic_unknown(
    csv_path: str | Path,
    seq_len: int = PPI_LEN,
    noise_per_split: dict[str, int] | None = None,
    noise_ratio: float = 0.10,
    seed: int = 599,
    noise_families: dict[str, str] | None = None,
) -> dict[str, int]:
    """Append deterministic synthetic unknown flows to an exported CSV.

    The generated packets are sampled from robust train statistics and then
    independently perturbed.  They are deliberately tagged with a string
    ``source`` column so they cannot be confused with held-out DataZoo
    unknown applications during reporting.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    noise_per_split = dict(noise_per_split or {})
    rng = np.random.default_rng(seed)
    noise_families = {**DEFAULT_NOISE_FAMILIES, **(noise_families or {})}
    known_flows_by_split = Counter()
    reservoir: list[tuple[float, float, float]] = []
    reservoir_limit = 10000
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{csv_path} has no CSV header")
        for row_index, row in enumerate(reader):
            split = str(row.get("split", "")).lower()
            if split == "train":
                try:
                    item = (float(row["size"]), float(row["direction"]), float(row["delta_time"]))
                    if len(reservoir) < reservoir_limit:
                        reservoir.append(item)
                    else:
                        replacement = int(rng.integers(0, row_index + 1))
                        if replacement < reservoir_limit:
                            reservoir[replacement] = item
                except (KeyError, TypeError, ValueError):
                    continue
            if (
                split in {"train", "val", "test"}
                and str(row.get("pkt_index", "")) == "0"
                and str(row.get("label", "")).strip().lower()
                not in {UNKNOWN_LABEL, "_unknown", "__unknown__"}
            ):
                known_flows_by_split[split] += 1
    if not reservoir:
        raise ValueError(f"No valid train rows found in {csv_path}")
    train_arr = np.asarray(reservoir, dtype=np.float32)
    center = np.nanmedian(train_arr, axis=0)
    scale = np.nanpercentile(train_arr, 75, axis=0) - np.nanpercentile(train_arr, 25, axis=0)
    scale = np.maximum(np.nan_to_num(scale, nan=1.0), 1e-3)
    direction_values = np.unique(train_arr[:, 1])
    if direction_values.size == 0:
        direction_values = np.asarray([0.0, 1.0], dtype=np.float32)

    default_counts = {
        split: int(round(known_flows_by_split.get(split, 0) * noise_ratio))
        for split in ("train", "val", "test")
    }
    counts = {split: int(noise_per_split.get(split, default_counts[split])) for split in ("train", "val", "test")}
    # Appending is safe because export_csv writes a stable header.  Retain
    # compatibility with older CSVs by only writing columns present in them.
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        fieldnames = list(csv.DictReader(handle).fieldnames or [])
    if not fieldnames:
        raise ValueError(f"{csv_path} has no CSV header")
    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        output_rows = []
        for split in ("train", "val", "test"):
            for flow_index in range(counts[split]):
                flow_id = f"synthetic_{split}_{flow_index}"
                family = str(noise_families[split])
                # All parameters come from train rows.  Families deliberately
                # differ by split so validation/test unknowns are generated by
                # mechanisms absent from training.
                if family == "gaussian_iid_v1":
                    flow = rng.normal(center, scale * 2.5, size=(seq_len, 3)).astype(np.float32)
                elif family == "shuffle_spike_v2":
                    flow = rng.normal(center, scale * 1.75, size=(seq_len, 3)).astype(np.float32)
                    for channel in (0, 2):
                        flow[:, channel] = rng.permutation(flow[:, channel])
                    spike_count = max(1, seq_len // 8)
                    spike_idx = rng.choice(seq_len, spike_count, replace=False)
                    flow[spike_idx, 0] += rng.normal(scale=scale[0] * 8.0, size=spike_count)
                    flow[spike_idx, 2] += rng.normal(scale=scale[2] * 8.0, size=spike_count)
                elif family == "mixture_burst_v3":
                    component = rng.integers(0, 2, size=(seq_len, 1))
                    broad = rng.normal(center, scale * 0.75, size=(seq_len, 3))
                    burst = rng.normal(center, scale * 5.0, size=(seq_len, 3))
                    flow = np.where(component == 0, broad, burst).astype(np.float32)
                    start = int(rng.integers(0, max(1, seq_len - 4)))
                    flow[start : start + 4, 0] *= 4.0
                else:
                    raise ValueError(f"unknown synthetic noise family: {family}")
                flow[:, 0] = np.clip(np.abs(flow[:, 0]), 0.0, 2**16 - 1)
                flow[:, 1] = rng.choice(direction_values, size=seq_len)
                flow[:, 2] = np.clip(np.abs(flow[:, 2]), 0.0, None)
                for pkt_index, (size, direction, delta_time) in enumerate(flow):
                    row = {
                        "flow_id": flow_id,
                        "label": UNKNOWN_LABEL,
                        "pkt_index": pkt_index,
                        "size": float(size),
                        "direction": float(direction),
                        "delta_time": float(delta_time),
                        "split": split,
                        "source": "synthetic_noise",
                        "original_app": f"synthetic_noise::{family}",
                        "source_group": f"noise_{split}",
                        "noise_family": family,
                        "capture_date": "",
                        "source_flow_id": f"synthetic::{split}::{family}::{flow_index}",
                    }
                    output_rows.append(tuple(row.get(field, "") for field in fieldnames))
                    if len(output_rows) >= 4096:
                        writer.writerows(output_rows)
                        output_rows.clear()
        if output_rows:
            writer.writerows(output_rows)
    append_synthetic_unknown.last_metadata = {
        "noise_families": noise_families,
        "source_groups": {split: f"noise_{split}" for split in ("train", "val", "test")},
        "seed": int(seed),
        "parameters_fit_from": "train_rows",
    }
    return counts


def limit_real_unknown_ratio(csv_path: str | Path, ratio: float = 0.30, seed: int = 599) -> dict:
    """Reduce real unknown flows to a per-split budget using source balancing.

    The DataZoo export must scan all complement applications to build an
    auditable candidate list. This second streaming pass keeps only the
    requested fraction and never duplicates or mixes application identities.
    """
    path = Path(csv_path)
    known_counts = Counter()
    app_counts: dict[str, Counter] = {s: Counter() for s in SPLITS}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        for row in reader:
            split = str(row.get("split", "")).lower()
            if split not in SPLITS:
                continue
            if row.get("pkt_index") == "0":
                label = str(row.get("label", "")).lower()
                if label != UNKNOWN_LABEL:
                    known_counts[split] += 1
                else:
                    app_counts[split][str(row.get("original_app", ""))] += 1
    budgets = {s: int(round(known_counts[s] * float(ratio))) for s in SPLITS}
    keep: dict[str, set[str]] = {s: set() for s in SPLITS}
    for split in SPLITS:
        apps = sorted(app_counts[split])
        rng_split = np.random.default_rng(seed + sum(ord(c) for c in split))
        rng_split.shuffle(apps)
        selected = {app: 0 for app in apps}
        selected_total = 0
        # The first pass gives each source one flow, then fills round-robin.
        while selected_total < budgets[split] and apps:
            progressed = False
            for app in apps:
                if selected[app] < app_counts[split][app]:
                    selected[app] += 1
                    selected_total += 1
                    progressed = True
                    if selected_total >= budgets[split]:
                        break
            if not progressed:
                break
        unknown_seen: dict[str, int] = Counter()
        seen_flow: set[str] = set()
        reservoirs: dict[str, list[str]] = {app: [] for app in apps}
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            has_packet_index = "pkt_index" in (reader.fieldnames or [])
            for row in reader:
                if str(row.get("split", "")).lower() != split or str(row.get("label", "")).lower() != UNKNOWN_LABEL:
                    continue
                if has_packet_index and str(row.get("pkt_index", "")) != "0":
                    continue
                app = str(row.get("original_app", ""))
                flow_id = str(row.get("flow_id", ""))
                if not has_packet_index:
                    if not flow_id or flow_id in seen_flow:
                        continue
                    seen_flow.add(flow_id)
                if has_packet_index or flow_id:
                    index = unknown_seen[app]
                    unknown_seen[app] += 1
                    quota = selected.get(app, 0)
                    if quota <= 0:
                        continue
                    reservoir = reservoirs[app]
                    if len(reservoir) < quota:
                        reservoir.append(flow_id)
                    else:
                        replacement = int(rng_split.integers(0, index + 1))
                        if replacement < quota:
                            reservoir[replacement] = flow_id
        for reservoir in reservoirs.values():
            keep[split].update(reservoir)
    temp = path.with_suffix(path.suffix + ".tmp")
    with path.open("r", newline="", encoding="utf-8-sig") as src, temp.open("w", newline="", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        writer = csv.writer(dst)
        writer.writerow(fields)
        output_rows = []
        for row in reader:
            if str(row.get("label", "")).lower() == UNKNOWN_LABEL and str(row.get("flow_id", "")) not in keep.get(str(row.get("split", "")).lower(), set()):
                continue
            output_rows.append(tuple(row.get(field, "") for field in fields))
            if len(output_rows) >= 4096:
                writer.writerows(output_rows)
                output_rows.clear()
        if output_rows:
            writer.writerows(output_rows)
    os.replace(temp, path)
    return {"requested_by_split": budgets, "actual_by_split": {s: len(keep[s]) for s in SPLITS},
            "available_by_split": {s: int(sum(app_counts[s].values())) for s in SPLITS}}


def _rescan_counts(csv_path: str | Path, classes: list[str]):
    counts = {s: Counter() for s in SPLITS}
    packet_counts = {s: Counter() for s in SPLITS}
    total = 0
    with Path(csv_path).open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            split, label = str(row.get("split", "")).lower(), str(row.get("label", ""))
            if split not in SPLITS:
                continue
            if str(row.get("pkt_index", "")) == "0":
                counts[split][label] += 1
            packet_counts[split][label] += 1
            total += 1
    return counts, total, packet_counts


def export_datazoo_open_set(
    dataset_name: str,
    size: str,
    project_root: str | Path,
    out_csv: str | Path | None = None,
    seq_len: int = PPI_LEN,
    topk: int = 60,
    classes: list[str] | None = None,
    scan_batches: int = 300,
    max_train_per_class: int | None = 10000,
    max_val_per_class: int | None = 2000,
    max_test_per_class: int | None = 2000,
    init_train_size: int | str = "all",
    init_val_size: int | str = "all",
    init_test_size: int | str = "all",
    datazoo_batch_size: int = 64,
    datazoo_test_batch_size: int = 64,
    datazoo_workers: int = 0,
    unknown_count: int | None = None,
    unknown_split_seed: int = 599,
    noise_ratio: float = 0.10,
    noise_seed: int = 599,
    unknown_ratio: float = 0.30,
    temporal_split: bool = True,
    max_export_batches: int | None = None,
):
    dataset_name = dataset_name.lower()
    size = size.upper()
    root = Path(project_root).resolve()
    dataset, dataset_root = build_dataset(
        dataset_name,
        size,
        root,
        train_size=init_train_size,
        val_size=init_val_size,
        test_size=init_test_size,
        batch_size=datazoo_batch_size,
        test_batch_size=datazoo_test_batch_size,
        workers=datazoo_workers,
        known_topk=topk,
        unknown_count=unknown_count,
        unknown_split_seed=unknown_split_seed,
        temporal_split=temporal_split,
    )
    if out_csv is None:
        out_csv = root / "data" / "processed" / f"datazoo_{dataset_name}{topk}_{size.lower()}.csv"
    if classes is None:
        classes = [str(x) for x in getattr(dataset, "_hsta_known_apps", getattr(dataset.class_info, "known_apps", []))]
        scan_counter = Counter()
        if not classes:
            classes, scan_counter = scan_classes(dataset, topk=topk, scan_batches=scan_batches)
    else:
        classes = [str(x) for x in classes]
        scan_counter = Counter()

    unknown_groups = getattr(dataset, "_hsta_unknown_groups", {})
    unknown_pool = list(getattr(dataset, "_hsta_unknown_apps", []))
    counts, packet_rows, packet_row_counts = export_csv(
        dataset,
        out_csv=out_csv,
        classes=classes,
        seq_len=seq_len,
        max_per_class_by_split={
            "train": max_train_per_class,
            "val": max_val_per_class,
            "test": max_test_per_class,
        },
        include_unknown=bool(unknown_pool),
        unknown_source_labels=set(),
        unknown_source_groups=unknown_groups,
        max_batches_per_split=max_export_batches,
    )
    real_unknown = limit_real_unknown_ratio(out_csv, ratio=unknown_ratio, seed=unknown_split_seed)
    counts, packet_rows, packet_row_counts = _rescan_counts(out_csv, classes)
    noise_counts = append_synthetic_unknown(
        out_csv,
        seq_len=seq_len,
        noise_ratio=noise_ratio,
        seed=noise_seed,
    )
    for split, flow_count in noise_counts.items():
        counts.setdefault(split, Counter())[UNKNOWN_LABEL] += int(flow_count)
        packet_row_counts.setdefault(split, Counter())[UNKNOWN_LABEL] += int(flow_count) * int(seq_len)
        packet_rows += int(flow_count) * int(seq_len)
    source_counts = scan_processed_source_counts(out_csv)
    report_classes = list(classes) + ([UNKNOWN_LABEL] if unknown_pool else [])
    servicemap_path = infer_servicemap_path(dataset_name, size=size, project_root=root)
    service_by_id = load_servicemap(servicemap_path)
    class_summary, class_count_summary = build_class_report(
        report_classes,
        counts,
        packet_row_counts,
        service_by_id=service_by_id,
    )
    report = {
        "dataset": dataset_name,
        "size": size,
        "dataset_root": _project_path(dataset_root, root),
        "out_csv": _project_path(out_csv, root),
        "servicemap_path": _project_path(servicemap_path, root) if servicemap_path else "",
        "seq_len": seq_len,
        "classes": report_classes,
        "unknown_label": UNKNOWN_LABEL if unknown_pool else "",
        "known_apps": [str(x) for x in getattr(dataset, "_hsta_known_apps", classes)],
        "known_app_selection": {
            "method": ("H5 global training-window APP frequency descending" if topk else "DataZoo ALL_KNOWN"),
            "background_apps_excluded": True,
            "requested_topk": int(topk),
            "selected_count": int(len(classes)),
            "ranking": getattr(dataset, "_hsta_selection_ranking", []),
        },
        "unknown_apps": unknown_pool,
        "unknown_candidate_pool": unknown_pool,
        "unknown_candidate_pool_complete": bool(getattr(dataset, "_hsta_unknown_pool_complete", False)),
        "unknown_candidate_flow_count_by_split": {
            split: int(sum(
                source_counts["source_group"][split].get(group, 0)
                for group in ("unknown_support", "unknown_val_heldout", "unknown_test_heldout")
            ))
            for split in SPLITS
        },
        "unknown_application_groups": unknown_groups,
        "unknown_split_seed": int(unknown_split_seed),
        "synthetic_noise_flows_by_split": noise_counts,
        "real_unknown_requested_by_split": real_unknown["requested_by_split"],
        "real_unknown_actual_by_split": real_unknown["actual_by_split"],
        "real_unknown_available_by_split": real_unknown["available_by_split"],
        "real_unknown_actual_ratio_by_split": {
            split: (real_unknown["actual_by_split"][split] /
                    max(sum(counts[split].get(label, 0) for label in classes), 1)) for split in SPLITS
        },
        "synthetic_noise": getattr(append_synthetic_unknown, "last_metadata", {}),
        "temporal_split": bool(temporal_split),
        # Keep the exact date lists in every export report so a sampled CSV
        # can be audited without relying on the code version that produced it.
        "temporal_date_splits": (
            TEMPORAL_DATE_SPLITS.get(dataset_name, {}) if temporal_split else {}
        ),
        "temporal_window_lengths": (
            {
                split: len(values)
                for split, values in TEMPORAL_DATE_SPLITS.get(dataset_name, {}).items()
            }
            if temporal_split
            else {}
        ),
        "scan_counter_top30": dict(scan_counter.most_common(30)),
        "flow_count_by_split": _split_counter_dict(counts),
        "packet_row_count_by_split": _split_counter_dict(packet_row_counts),
        "source_group_flow_count_by_split": _split_counter_dict(source_counts["source_group"]),
        "original_app_flow_count_by_split": _split_counter_dict(source_counts["original_app"]),
        "packet_rows": packet_rows,
        "class_summary": class_summary,
        "class_count_summary": class_count_summary,
        "max_train_per_class": max_train_per_class,
        "max_val_per_class": max_val_per_class,
        "max_test_per_class": max_test_per_class,
        "init_train_size": init_train_size,
        "init_val_size": init_val_size,
        "init_test_size": init_test_size,
        "datazoo_batch_size": datazoo_batch_size,
        "datazoo_test_batch_size": datazoo_test_batch_size,
        "datazoo_workers": datazoo_workers,
        "unknown_count": None if unknown_count is None else int(unknown_count),
        "noise_ratio": float(noise_ratio),
        "unknown_ratio": float(unknown_ratio),
        "random_seeds": {"dataset": 599, "unknown_split": int(unknown_split_seed), "noise": int(noise_seed)},
        "global_topk": bool(getattr(dataset, "_hsta_global_topk", False)),
    }
    manifest_path = Path(out_csv).with_suffix(".manifest.json")
    manifest = {
        "dataset": dataset_name,
        "size": size,
        "seed": 599,
        "random_seeds": report["random_seeds"],
        "temporal_date_splits": report["temporal_date_splits"],
        "known_apps": report["known_apps"],
        "known_app_selection": report["known_app_selection"],
        "unknown_candidate_pool": report["unknown_candidate_pool"],
        "unknown_application_groups": report["unknown_application_groups"],
        "real_unknown_requested_by_split": report.get("real_unknown_requested_by_split", {}),
        "real_unknown_available_by_split": report.get("real_unknown_available_by_split", {}),
        "real_unknown_actual_by_split": report.get("real_unknown_actual_by_split", {}),
        "noise_ratio": float(noise_ratio),
        "noise_families": report.get("synthetic_noise", {}).get("noise_families", {}),
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    report["manifest_path"] = _project_path(manifest_path, root)
    report_path = Path(out_csv).with_suffix(".report.json")
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report
