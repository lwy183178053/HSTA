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


def _imports():
    from cesnet_datazoo.config import AppSelection, DatasetConfig
    from cesnet_datazoo.datasets import CESNET_QUIC22, CESNET_TLS22

    return CESNET_TLS22, CESNET_QUIC22, DatasetConfig, AppSelection


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
            "out_csv": str(csv_path.resolve()),
            "servicemap_path": str(servicemap_path.resolve()) if servicemap_path else "",
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
):
    CESNET_TLS22, CESNET_QUIC22, DatasetConfig, AppSelection = _imports()
    root = Path(project_root).resolve()
    size = size.upper()
    if name == "tls":
        dataset_root = root / "data" / "raw" / "cesnet_tls22_datazoo"
        dataset = CESNET_TLS22(str(dataset_root), size=size)
        cfg = DatasetConfig(
            dataset=dataset,
            apps_selection=AppSelection.ALL_KNOWN,
            train_period_name="W-2021-40",
            test_period_name="W-2021-41",
            train_size=train_size,
            val_known_size=val_size,
            test_known_size=test_size,
            val_unknown_size=0,
            test_unknown_size=0,
            batch_size=batch_size,
            test_batch_size=test_batch_size,
            train_workers=workers,
            val_workers=workers,
            test_workers=workers,
        )
    elif name == "quic":
        dataset_root = root / "data" / "raw" / "cesnet_quic22_datazoo"
        dataset = CESNET_QUIC22(str(dataset_root), size=size)
        cfg = DatasetConfig(
            dataset=dataset,
            apps_selection=AppSelection.ALL_KNOWN,
            train_period_name="W-2022-44",
            test_period_name="W-2022-45",
            train_size=train_size,
            val_known_size=val_size,
            test_known_size=test_size,
            val_unknown_size=0,
            test_unknown_size=0,
            batch_size=batch_size,
            test_batch_size=test_batch_size,
            train_workers=workers,
            val_workers=workers,
            test_workers=workers,
        )
    else:
        raise ValueError(f"Unknown dataset: {name}")
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
):
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    selected = set(classes)
    split_counts = {split: Counter() for split in ["train", "val", "test"]}
    packet_row_counts = {split: Counter() for split in ["train", "val", "test"]}
    split_caps = {"train": None, "val": None, "test": None}
    split_caps.update(max_per_class_by_split or {})
    packet_rows = 0
    with out_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["flow_id", "label", "pkt_index", "size", "direction", "delta_time", "split"],
        )
        writer.writeheader()
        for split in ["train", "val", "test"]:
            split_cap = split_caps.get(split)
            flow_index = 0
            for batch in tqdm(get_loader(dataset, split), desc=f"export {split}"):
                for ppi_one, label_raw in iter_batch(batch):
                    label = decode_label(label_raw, dataset)
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
                            }
                        )
                        packet_rows += 1
                        packet_row_counts[split][label] += 1
                if split_cap and all(split_counts[split][c] >= split_cap for c in classes):
                    break
    return split_counts, packet_rows, packet_row_counts


def export_datazoo_8class(
    dataset_name: str,
    size: str,
    project_root: str | Path,
    out_csv: str | Path | None = None,
    seq_len: int = 30,
    topk: int = 8,
    classes: list[str] | None = None,
    scan_batches: int = 300,
    max_train_per_class: int | None = 10000,
    max_val_per_class: int | None = 2000,
    max_test_per_class: int | None = 2000,
    init_train_size: int | str = 500000,
    init_val_size: int | str = 200000,
    init_test_size: int | str = 200000,
    datazoo_batch_size: int = 64,
    datazoo_test_batch_size: int = 64,
    datazoo_workers: int = 0,
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
    )
    if out_csv is None:
        out_csv = root / "data" / "processed" / f"datazoo_{dataset_name}{topk}_{size.lower()}_seq{seq_len}.csv"
    if classes is None:
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
    )
    servicemap_path = infer_servicemap_path(dataset_name, size=size, project_root=root)
    service_by_id = load_servicemap(servicemap_path)
    class_summary, class_count_summary = build_class_report(
        classes,
        counts,
        packet_row_counts,
        service_by_id=service_by_id,
    )
    report = {
        "dataset": dataset_name,
        "size": size,
        "dataset_root": str(dataset_root),
        "out_csv": str(Path(out_csv).resolve()),
        "servicemap_path": str(servicemap_path.resolve()) if servicemap_path else "",
        "seq_len": seq_len,
        "classes": classes,
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
    }
    report_path = Path(out_csv).with_suffix(".report.json")
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report
