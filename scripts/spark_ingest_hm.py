"""Spark ingestion for the H&M ZIP/CSV files.

The ZIP extraction is a staging concern. All tabular reading, casting,
partitioning, and writes happen through Spark DataFrames.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date


def materialize_csv(path: Path, staging: Path) -> Path:
    if path.suffix.lower() != ".zip":
        return path
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"Expected exactly one CSV in {path}, found {members}")
        target = staging / Path(members[0]).name
        with archive.open(members[0]) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=8 * 1024 * 1024)
        return target


def read_csv(spark: SparkSession, path: Path):
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .option("mode", "FAILFAST")
        .csv(str(path))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=Path, required=True)
    parser.add_argument("--customers", type=Path, required=True)
    parser.add_argument("--articles", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/bronze"))
    parser.add_argument("--master", default=None, help="Spark master, e.g. local[*] or spark://spark-master:7077")
    args = parser.parse_args()

    builder = SparkSession.builder.appName("hm-spark-ingest")
    if args.master:
        builder = builder.master(args.master)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    # Keep all temporary extraction on the configured output drive. The default
    # Windows TEMP may be on C:, which is deliberately not used by this project.
    staging = Path(tempfile.mkdtemp(prefix="hm-csv-staging-", dir=args.output))
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        customers = read_csv(spark, materialize_csv(args.customers, staging))
        articles = read_csv(spark, materialize_csv(args.articles, staging))
        transactions = read_csv(spark, materialize_csv(args.transactions, staging)).withColumn("t_dat", to_date("t_dat"))

        customers.write.mode("overwrite").parquet(str(args.output / "customers.parquet"))
        articles.write.mode("overwrite").parquet(str(args.output / "articles.parquet"))
        transactions.repartition("t_dat").write.mode("overwrite").partitionBy("t_dat").parquet(str(args.output / "transactions"))
        print("Spark ingestion completed")
    finally:
        spark.stop()
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()

