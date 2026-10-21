"""Train a reproducible popularity/affinity retrieval artifact from H&M Parquet."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl


def train(transactions: Path, articles: Path, output: Path, test_days: int = 30) -> dict:
    tx = pl.scan_parquet(str(transactions / "**" / "*.parquet"), hive_partitioning=True).with_columns(
        pl.col("article_id").cast(pl.Utf8),
        pl.col("customer_id").cast(pl.Utf8),
    )
    article = pl.scan_parquet(str(articles)).select([
        pl.col("article_id").cast(pl.Utf8),
        pl.col("product_type_name"),
        pl.col("department_name"),
        pl.col("colour_group_name"),
    ])
    max_date = tx.select(pl.col("t_dat").max()).collect().item()
    cutoff = max_date
    # Keep a time-based holdout rather than randomly leaking future purchases into training.
    test_start = cutoff - timedelta(days=test_days)
    train_tx = tx.filter(pl.col("t_dat") <= test_start)
    if train_tx.select(pl.len()).collect().item() == 0:
        train_tx = tx

    popularity = (
        train_tx.group_by("article_id")
        .agg(pl.len().alias("purchases"), pl.col("t_dat").max().alias("last_seen"))
        .sort(["purchases", "last_seen"], descending=[True, True])
        .collect()
    )
    customer_affinity = (
        train_tx.join(article, on="article_id", how="left")
        .group_by(["customer_id", "department_name"])
        .agg(pl.len().alias("interactions"))
        .collect()
    )
    customer_top_affinity = (
        customer_affinity.sort(["customer_id", "interactions"], descending=[False, True])
        .group_by("customer_id", maintain_order=True)
        .head(3)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    popularity.write_parquet(output.with_suffix(".popularity.parquet"), compression="zstd")
    customer_affinity.write_parquet(output.with_suffix(".customer_affinity.parquet"), compression="zstd")
    customer_top_affinity.write_parquet(output.with_suffix(".customer_top_affinity.parquet"), compression="zstd")
    metadata = {
        "model_version": output.stem,
        "trained_at": date.today().isoformat(),
        "training_cutoff": str(cutoff),
        "test_days": test_days,
        "popular_articles": popularity.height,
        "customer_affinity_rows": customer_affinity.height,
        "customer_top_affinity_rows": customer_top_affinity.height,
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=Path, default=Path("data/bronze/transactions"))
    parser.add_argument("--articles", type=Path, default=Path("data/bronze/articles.parquet"))
    parser.add_argument("--output", type=Path, default=Path("models/artifacts/hm_baseline_v1"))
    args = parser.parse_args()
    print(json.dumps(train(args.transactions, args.articles, args.output), indent=2))


if __name__ == "__main__":
    main()

