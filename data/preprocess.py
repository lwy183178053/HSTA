from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .sampler import PPI_LEN, enrich_processed_report, export_datazoo_open_set


def parse_size(value: str):
    if value is None:
        return None
    value = str(value).strip().lower()
    if value in {"none", "null", "0"}:
        return None
    if value == "all":
        return "all"
    return int(value)


def parse_workers(value: str):
    value = str(value).strip().lower()
    if value == "auto":
        return value
    workers = int(value)
    if workers < 0:
        raise argparse.ArgumentTypeError("workers must be >= 0 or 'auto'")
    return workers


def ensure_datazoo_package():
    try:
        import cesnet_datazoo  # noqa: F401
    except Exception:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cesnet-datazoo"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["tls", "quic"], default=None)
    parser.add_argument("--size", default="S", choices=["S", "M", "L"])
    parser.add_argument(
        "--topk",
        type=int,
        default=60,
        help="number of known classes selected by DataZoo training frequency (default: 60)",
    )
    parser.add_argument(
        "--unknown-count",
        type=int,
        default=None,
        help="optional debugging cap; default uses every application outside the known top-k pool",
    )
    parser.add_argument("--unknown-split-seed", type=int, default=599)
    parser.add_argument("--noise-ratio", type=float, default=0.10, help="synthetic unknown flows as a fraction of known flows")
    parser.add_argument("--noise-seed", type=int, default=599)
    parser.add_argument("--unknown-ratio", type=float, default=0.30,
                        help="real unknown flow budget as a fraction of known flows")
    parser.add_argument("--random-split", action="store_true", help="use DataZoo's random validation split instead of date windows")
    parser.add_argument("--classes", nargs="*", default=None)
    parser.add_argument("--scan-batches", type=int, default=100)
    parser.add_argument("--max-train-per-class", type=int, default=10000)
    parser.add_argument("--max-val-per-class", type=int, default=2000)
    parser.add_argument("--max-test-per-class", type=int, default=2000)
    parser.add_argument("--init-train-size", default="all")
    parser.add_argument("--init-val-size", default="all")
    parser.add_argument("--init-test-size", default="all")
    parser.add_argument("--datazoo-batch-size", type=int, default=64)
    parser.add_argument("--datazoo-test-batch-size", type=int, default=64)
    parser.add_argument("--datazoo-workers", type=parse_workers, default=0,
                        help="DataZoo HDF5 loader processes; use auto for CPU-aware capped parallelism")
    parser.add_argument("--max-export-batches", type=int, default=None)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--out-csv", default=None)
    parser.add_argument(
        "--enrich-existing-reports",
        action="store_true",
        help="Update existing processed CSV report JSON files with class mappings and counts, without re-exporting data.",
    )
    parser.add_argument(
        "--report-csv",
        nargs="*",
        type=Path,
        default=None,
        help="Processed CSV file(s) to enrich. Defaults to data/processed/*.csv.",
    )
    args = parser.parse_args()

    if args.enrich_existing_reports:
        project_root = Path(args.project_root)
        csv_paths = args.report_csv or sorted((project_root / "data" / "processed").glob("*.csv"))
        if not csv_paths:
            raise FileNotFoundError("No processed CSV files found to enrich.")
        for csv_path in csv_paths:
            report = enrich_processed_report(csv_path, project_root=project_root)
            print("[OK] report:", str(Path(report["out_csv"]).with_suffix(".report.json")))
            print("[OK] classes:", report["class_count_summary"]["num_classes"])
        return

    if args.dataset is None:
        parser.error("--dataset is required unless --enrich-existing-reports is used")

    ensure_datazoo_package()
    report = export_datazoo_open_set(
        dataset_name=args.dataset,
        size=args.size,
        project_root=Path(args.project_root).resolve(),
        out_csv=args.out_csv,
        seq_len=PPI_LEN,
        topk=args.topk,
        classes=args.classes,
        scan_batches=args.scan_batches,
        max_train_per_class=args.max_train_per_class,
        max_val_per_class=args.max_val_per_class,
        max_test_per_class=args.max_test_per_class,
        init_train_size=parse_size(args.init_train_size),
        init_val_size=parse_size(args.init_val_size),
        init_test_size=parse_size(args.init_test_size),
        datazoo_batch_size=args.datazoo_batch_size,
        datazoo_test_batch_size=args.datazoo_test_batch_size,
        datazoo_workers=args.datazoo_workers,
        unknown_count=args.unknown_count,
        unknown_split_seed=args.unknown_split_seed,
        noise_ratio=args.noise_ratio,
        unknown_ratio=args.unknown_ratio,
        noise_seed=args.noise_seed,
        temporal_split=not args.random_split,
        max_export_batches=args.max_export_batches,
    )
    print("[OK] csv:", report["out_csv"])
    print("[OK] report:", str(Path(report["out_csv"]).with_suffix(".report.json")))
    print("[OK] counts:", report["flow_count_by_split"])


if __name__ == "__main__":
    main()
