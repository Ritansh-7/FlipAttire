"""Evaluate a popularity recommender using a time-based H&M holdout."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

import polars as pl


def evaluate(transactions: Path, k: int = 12, test_days: int = 30) -> dict:
    frame = pl.read_parquet(str(transactions / "**" / "*.parquet"), hive_partitioning=True)
    max_date = frame["t_dat"].max()
    test_start = max_date - timedelta(days=test_days)
    train = frame.filter(pl.col("t_dat") <= test_start)
    test = frame.filter(pl.col("t_dat") > test_start)
    popular = train.group_by("article_id").len().sort("len", descending=True).head(k)["article_id"].to_list()
    truth = test.group_by("customer_id").agg(pl.col("article_id").unique().alias("items"))
    hits = sum(bool(set(row["items"]) & set(popular)) for row in truth.iter_rows(named=True))
    users = truth.height
    return {
        "model": "global_popularity",
        "k": k,
        "test_start": str(test_start),
        "test_users": users,
        "recall_at_k": hits / users if users else 0.0,
        "catalog_coverage_at_k": len(set(popular)) / train["article_id"].n_unique() if train.height else 0.0,
        "recommended_items": len(popular),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=Path, default=Path("data/bronze/transactions"))
    parser.add_argument("--k", type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.transactions, args.k), indent=2))


if __name__ == "__main__":
    main()

