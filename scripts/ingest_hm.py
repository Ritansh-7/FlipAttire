"""Ingest the official H&M Kaggle ZIP files into partitioned Parquet.

The transaction archive is streamed in batches, so the full CSV is never loaded
into memory. The output is suitable for Spark, DuckDB, Polars, or ClickHouse.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import polars as pl


def read_zip_table(path: Path, batch_size: int = 250_000):
    archive = zipfile.ZipFile(path)
    member = archive.namelist()[0]
    raw = archive.open(member)
    reader = pl.read_csv_batched(raw, batch_size=batch_size, infer_schema_length=10_000, try_parse_dates=True)
    return archive, raw, reader


def write_small(path: Path, output: Path) -> int:
    archive, raw, reader = read_zip_table(path, batch_size=100_000)
    try:
        batches = reader.next_batches(100_000)
        table = pl.concat(batches, how="vertical_relaxed")
        table.write_parquet(output, compression="zstd")
        return table.height
    finally:
        raw.close()
        archive.close()


def write_transactions(path: Path, output_dir: Path) -> tuple[int, int]:
    archive, raw, reader = read_zip_table(path)
    total = 0
    files = 0
    try:
        while batches := reader.next_batches(1):
            frame = batches[0].with_columns(pl.col("t_dat").cast(pl.Date))
            for date, partition in frame.partition_by("t_dat", as_dict=True).items():
                date_value = date[0] if isinstance(date, tuple) else date
                partition_dir = output_dir / f"t_dat={date_value}"
                partition_dir.mkdir(parents=True, exist_ok=True)
                partition.write_parquet(partition_dir / f"part-{files:06d}.parquet", compression="zstd")
                files += 1
            total += frame.height
            if total % 1_000_000 < len(frame):
                print(f"processed {total:,} transactions")
    finally:
        raw.close()
        archive.close()
    return total, files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=Path, required=True)
    parser.add_argument("--customers", type=Path, required=True)
    parser.add_argument("--articles", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/bronze"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    customers = write_small(args.customers, args.output / "customers.parquet")
    articles = write_small(args.articles, args.output / "articles.parquet")
    transactions, files = write_transactions(args.transactions, args.output / "transactions")
    print({"customers": customers, "articles": articles, "transactions": transactions, "transaction_files": files})


if __name__ == "__main__":
    main()

