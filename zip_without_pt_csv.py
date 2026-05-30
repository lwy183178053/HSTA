from __future__ import annotations

import argparse
import zipfile
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
EXCLUDED_SUFFIXES = {".pt", ".csv"}


def should_include(path: Path, output_zip: Path) -> bool:
    if not path.is_file():
        return False
    if path.resolve() == output_zip.resolve():
        return False
    return path.suffix.lower() not in EXCLUDED_SUFFIXES


def _write_file(
    zf: zipfile.ZipFile,
    path: Path,
    arcname: Path,
    added: set[str],
) -> tuple[int, int]:
    key = arcname.as_posix()
    if key in added:
        return 0, 0
    zf.write(path, arcname)
    added.add(key)
    return 1, path.stat().st_size


def zip_without_pt_csv(
    source_dir: Path,
    output_zip: Path,
    *,
    include_data_reports: bool = True,
    data_report_dir: Path = PROJECT_ROOT / "data" / "processed",
) -> tuple[int, int]:
    source_dir = source_dir.resolve()
    output_zip = output_zip.resolve()
    data_report_dir = data_report_dir.resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    file_count = 0
    total_bytes = 0
    added: set[str] = set()
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if not should_include(path, output_zip):
                continue
            count, size = _write_file(zf, path, path.relative_to(source_dir), added)
            file_count += count
            total_bytes += size

        if include_data_reports and data_report_dir.exists():
            for path in sorted(data_report_dir.glob("*.report.json")):
                if not should_include(path, output_zip):
                    continue
                arcname = path.relative_to(PROJECT_ROOT)
                count, size = _write_file(zf, path, arcname, added)
                file_count += count
                total_bytes += size

    return file_count, total_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zip result files except .pt and .csv, optionally including processed dataset reports."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "results",
        help="Directory to package. Defaults to ./results.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output zip path. Defaults to <source>_without_pt_csv_<timestamp>.zip.",
    )
    parser.add_argument(
        "--include-data-reports",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include data/processed/*.report.json with dataset counts and label mappings. Default: enabled.",
    )
    parser.add_argument(
        "--data-report-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Directory containing *.report.json files to include.",
    )
    args = parser.parse_args()

    source_dir = args.source.resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise NotADirectoryError(f"Source directory not found: {source_dir}")

    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_zip = source_dir.parent / f"{source_dir.name}_without_pt_csv_{timestamp}.zip"
    else:
        output_zip = args.output.resolve()

    file_count, total_bytes = zip_without_pt_csv(
        source_dir,
        output_zip,
        include_data_reports=args.include_data_reports,
        data_report_dir=args.data_report_dir,
    )
    print(f"Created: {output_zip}")
    print(f"Files: {file_count}")
    print(f"Uncompressed bytes: {total_bytes}")
    if args.include_data_reports:
        print(f"Included dataset reports from: {args.data_report_dir.resolve()}")


if __name__ == "__main__":
    main()
