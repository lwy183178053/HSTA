from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .sampler import enrich_processed_report, export_datazoo_8class


def parse_size(value: str):
    if value is None:
        return None
    value = str(value).strip().lower()
    if value in {"none", "null", "0"}:
        return None
    if value == "all":
        return "all"
    return int(value)


def ensure_datazoo_package():
    try:
        import cesnet_datazoo  # noqa: F401
    except Exception:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cesnet-datazoo"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["tls", "quic"], default=None)
    parser.add_argument("--size", default="S", choices=["XS", "S", "M", "L"])
    parser.add_argument("--seq-len", type=int, default=30)
    parser.add_argument("--topk", type=int, default=40)
    parser.add_argument("--classes", nargs="*", default=None)
    parser.add_argument("--scan-batches", type=int, default=300)
    parser.add_argument("--max-train-per-class", type=int, default=10000)
    parser.add_argument("--max-val-per-class", type=int, default=2000)
    parser.add_argument("--max-test-per-class", type=int, default=2000)
    parser.add_argument("--init-train-size", default="1000000")
    parser.add_argument("--init-val-size", default="200000")
    parser.add_argument("--init-test-size", default="200000")
    parser.add_argument("--datazoo-batch-size", type=int, default=64)
    parser.add_argument("--datazoo-test-batch-size", type=int, default=64)
    parser.add_argument("--datazoo-workers", type=int, default=0)
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
    report = export_datazoo_8class(
        dataset_name=args.dataset,
        size=args.size,
        project_root=Path(args.project_root),
        out_csv=args.out_csv,
        seq_len=args.seq_len,
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
    )
    print("[OK] csv:", report["out_csv"])
    print("[OK] report:", str(Path(report["out_csv"]).with_suffix(".report.json")))
    print("[OK] counts:", report["flow_count_by_split"])


if __name__ == "__main__":
    main()
