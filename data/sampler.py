from __future__ import annotations

import csv
import json
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


def _project_path(path: str | Path, project_root: str | Path) -> str:
    """Store portable project-relative paths in generated reports."""
    path = Path(path).resolve()
    root = Path(project_root).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _imports():
    from cesnet_datazoo.config import AppSelection, DatasetConfig, ValidationApproach
    from cesnet_datazoo.datasets import CESNET_QUIC22, CESNET_TLS22

    return CESNET_TLS22, CESNET_QUIC22, DatasetConfig, AppSelection, ValidationApproach


# The dates are disjoint and ordered.  This keeps validation genuinely
# forward-looking instead of drawing it randomly from the training week.
TEMPORAL_DATE_SPLITS = {
    "tls": {
        "train": ["20211004", "20211005", "20211006", "20211007", "20211008", "20211009"],
        "val": ["20211010"],
        "test": ["20211011", "20211012", "20211013", "20211014", "20211015", "20211016", "20211017"],
    },
    "quic": {
        "train": ["20221031", "20221101", "20221102", "20221103", "20221104", "20221105"],
        "val": ["20221106"],
        "test": ["20221107", "20221108", "20221109", "20221110", "20221111", "20221112", "20221113"],
    },
}
UNKNOWN_LABEL = "unknown"
PPI_LEN = 30


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


def _counter_dict(counter: Counter) -> dict[str, int]:
    return {str(key): int(counter[key]) for key in sorted(counter)}


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

        for row_index, row in enumerate(reader):
            label = str(row.get(label_col, "") or "")
            if not label:
                continue
            split = str(row.get(split_col, "all") if has_split else "all").lower()
            labels.add(label)
            row_counts_by_split[split][label] += 1
            total_rows += 1

            flow_id = str(row.get(flow_col, row_index) if has_flow else row_index)
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
    known_topk: int | None = 100,
    unknown_count: int = 5,
    temporal_split: bool = True,
):
    CESNET_TLS22, CESNET_QUIC22, DatasetConfig, AppSelection, ValidationApproach = _imports()
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
    # Reserve the final day of the train week for validation so no flow is
    # shared across the three temporal windows.
    train_period = dataset.default_train_period_name
    test_period = dataset.default_test_period_name

    def config_for(dataset, selection, **selection_kwargs):
        common = dict(
            dataset=dataset,
            apps_selection=selection,
            train_period_name=train_period,
            val_period_name=train_period,
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
            random_state=420,
            **selection_kwargs,
        )
        if not temporal_split:
            common.pop("train_dates")
            common.pop("val_dates")
            common.pop("test_dates")
        return DatasetConfig(**common)

    # First let DataZoo rank applications by actual training frequency.  A
    # second fixed configuration limits the open-world arm to only a few
    # explicit unknown applications; every other class is excluded.
    if known_topk and unknown_count > 0:
        probe_cfg = config_for(dataset, AppSelection.TOPX_KNOWN, apps_selection_topx=int(known_topk))
        dataset.set_dataset_config_and_initialize(probe_cfg)
        known_apps = [str(x) for x in dataset.class_info.known_apps]
        unknown_apps = [str(x) for x in dataset.class_info.unknown_apps[: int(unknown_count)]]
        if not unknown_apps:
            raise RuntimeError(f"No unknown applications available for {name} {size}")
        # Recreate the object so the generated index cache reflects the final
        # fixed known/unknown class list rather than the probe configuration.
        dataset = dataset_cls(str(dataset_root), size=size)
        cfg = config_for(
            dataset,
            AppSelection.FIXED,
            apps_selection_fixed_known=known_apps,
            apps_selection_fixed_unknown=unknown_apps,
        )
    elif known_topk:
        cfg = config_for(dataset, AppSelection.TOPX_KNOWN, apps_selection_topx=int(known_topk))
    else:
        cfg = config_for(dataset, AppSelection.ALL_KNOWN)
    dataset.set_dataset_config_and_initialize(cfg)
    return dataset, dataset_root


def get_loader(dataset, split: str):
    if split == "train":
        return dataset.get_train_dataloader()
    if split == "val":
        return dataset.get_val_dataloader()
    if split == "test":
        return dataset.get_test_dataloader()
    raise ValueError(split)


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
    max_batches_per_split: int | None = None,
):
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    selected = set(classes)
    unknown_source_labels = {str(label) for label in (unknown_source_labels or set())}
    selected.update(unknown_source_labels)
    if include_unknown:
        selected.add(UNKNOWN_LABEL)
    split_counts = {split: Counter() for split in ["train", "val", "test"]}
    packet_row_counts = {split: Counter() for split in ["train", "val", "test"]}
    split_caps = {"train": None, "val": None, "test": None}
    split_caps.update(max_per_class_by_split or {})
    packet_rows = 0
    with out_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["flow_id", "label", "pkt_index", "size", "direction", "delta_time", "split", "source"],
        )
        writer.writeheader()
        for split in ["train", "val", "test"]:
            split_cap = split_caps.get(split)
            flow_index = 0
            for batch_index, batch in enumerate(tqdm(get_loader(dataset, split), desc=f"export {split}")):
                for ppi_one, label_raw in iter_batch(batch):
                    label = decode_label(label_raw, dataset)
                    if label in unknown_source_labels:
                        label = UNKNOWN_LABEL
                    if label not in selected:
                        continue
                    if split_cap and split_counts[split][label] >= split_cap:
                        continue
                    times, dirs, sizes = parse_ppi(ppi_one, seq_len)
                    if len(sizes) == 0:
                        continue
                    flow_id = f"{split}_{flow_index}"
                    flow_index += 1
                    split_counts[split][label] += 1
                    for pkt_index in range(min(seq_len, len(sizes))):
                        writer.writerow(
                            {
                                "flow_id": flow_id,
                                "label": label,
                                "pkt_index": pkt_index,
                                "size": float(sizes[pkt_index]),
                                "direction": float(dirs[pkt_index]) if pkt_index < len(dirs) else 1.0,
                                "delta_time": float(times[pkt_index]) if pkt_index < len(times) else 0.0,
                                "split": split,
                                "source": "datazoo",
                            }
                        )
                        packet_rows += 1
                        packet_row_counts[split][label] += 1
                cap_labels = list(classes)
                if include_unknown and split != "train":
                    cap_labels.append(UNKNOWN_LABEL)
                if split_cap and all(split_counts[split][c] >= split_cap for c in cap_labels):
                    break
                if max_batches_per_split and batch_index + 1 >= max_batches_per_split:
                    break
    return split_counts, packet_rows, packet_row_counts


def append_synthetic_unknown(
    csv_path: str | Path,
    seq_len: int = PPI_LEN,
    noise_per_split: dict[str, int] | None = None,
    noise_ratio: float = 0.05,
    seed: int = 42,
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
    rows_by_split = Counter()
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
            rows_by_split[split] += 1
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
        split: int(round(rows_by_split.get(split, 0) / max(seq_len, 1) * noise_ratio))
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        for split in ("train", "val", "test"):
            for flow_index in range(counts[split]):
                flow_id = f"synthetic_{split}_{flow_index}"
                # Larger perturbations generate a broad unknown support while
                # keeping values in physically meaningful packet ranges.
                flow = rng.normal(center, scale * 2.5, size=(seq_len, 3)).astype(np.float32)
                flow[:, 0] = np.clip(np.abs(flow[:, 0]), 0.0, 2**16 - 1)
                flow[:, 1] = rng.choice(direction_values, size=seq_len)
                flow[:, 2] = np.clip(np.abs(flow[:, 2]), 0.0, None)
                for pkt_index, (size, direction, delta_time) in enumerate(flow):
                    writer.writerow(
                        {
                            "flow_id": flow_id,
                            "label": UNKNOWN_LABEL,
                            "pkt_index": pkt_index,
                            "size": float(size),
                            "direction": float(direction),
                            "delta_time": float(delta_time),
                            "split": split,
                            "source": "synthetic_noise",
                        }
                    )
    return counts


def export_datazoo_open_set(
    dataset_name: str,
    size: str,
    project_root: str | Path,
    out_csv: str | Path | None = None,
    seq_len: int = PPI_LEN,
    topk: int = 100,
    classes: list[str] | None = None,
    scan_batches: int = 300,
    max_train_per_class: int | None = 10000,
    max_val_per_class: int | None = 10000,
    max_test_per_class: int | None = 10000,
    init_train_size: int | str = "all",
    init_val_size: int | str = "all",
    init_test_size: int | str = "all",
    datazoo_batch_size: int = 64,
    datazoo_test_batch_size: int = 64,
    datazoo_workers: int = 0,
    unknown_count: int = 5,
    noise_ratio: float = 0.05,
    noise_seed: int = 42,
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
        temporal_split=temporal_split,
    )
    if out_csv is None:
        out_csv = root / "data" / "processed" / f"datazoo_{dataset_name}{topk}_{size.lower()}.csv"
    if classes is None:
        classes = [str(x) for x in getattr(dataset.class_info, "known_apps", [])]
        scan_counter = Counter()
        if not classes:
            classes, scan_counter = scan_classes(dataset, topk=topk, scan_batches=scan_batches)
    else:
        classes = [str(x) for x in classes]
        scan_counter = Counter()

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
        include_unknown=bool(unknown_count > 0),
        unknown_source_labels={str(x) for x in getattr(dataset.class_info, "unknown_apps", [])},
        max_batches_per_split=max_export_batches,
    )
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
    report_classes = list(classes) + ([UNKNOWN_LABEL] if unknown_count > 0 else [])
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
        "unknown_label": UNKNOWN_LABEL if unknown_count > 0 else "",
        "unknown_apps": [str(x) for x in getattr(dataset.class_info, "unknown_apps", [])],
        "synthetic_noise_flows_by_split": noise_counts,
        "temporal_split": bool(temporal_split),
        "scan_counter_top30": dict(scan_counter.most_common(30)),
        "flow_count_by_split": _split_counter_dict(counts),
        "packet_row_count_by_split": _split_counter_dict(packet_row_counts),
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
        "unknown_count": int(unknown_count),
        "noise_ratio": float(noise_ratio),
    }
    report_path = Path(out_csv).with_suffix(".report.json")
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report
