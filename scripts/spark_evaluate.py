"""Time-based Recall@K evaluation with Spark SQL/DataFrames."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import array_intersect, avg, collect_set, col, count, lit, max as spark_max, size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=Path, default=Path("data/bronze/transactions"))
    parser.add_argument("--k", type=int, default=12)
    parser.add_argument("--test-days", type=int, default=30)
    parser.add_argument("--master", default=None)
    args = parser.parse_args()
    if args.k < 1 or args.test_days < 1:
        parser.error("--k and --test-days must both be positive")

    builder = SparkSession.builder.appName("hm-spark-evaluate")
    if args.master:
        builder = builder.master(args.master)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        tx = spark.read.parquet(str(args.transactions)).select("customer_id", "article_id", "t_dat")
        cutoff = tx.select(spark_max("t_dat")).first()[0]
        if cutoff is None:
            raise ValueError("cannot evaluate recommendations on an empty transaction dataset")
        test_start = cutoff - timedelta(days=args.test_days)
        train = tx.where(col("t_dat") <= test_start)
        test = tx.where(col("t_dat") > test_start)
        popular = [
            row["article_id"]
            for row in train.groupBy("article_id")
            .count()
            .orderBy(col("count").desc(), col("article_id").asc())
            .limit(args.k)
            .collect()
        ]
        if not popular:
            raise ValueError("the training window contains no articles to recommend")
        seen = train.select("customer_id", "article_id").distinct()
        novel_test = test.join(seen, ["customer_id", "article_id"], "left_anti")
        truth = novel_test.groupBy("customer_id").agg(collect_set("article_id").alias("truth"))
        recommended = truth.withColumn("recommended", lit(popular))
        measured = (
            recommended.withColumn("hits", size(array_intersect("truth", "recommended")))
            .withColumn("recall", col("hits") / size("truth"))
            .withColumn("precision", col("hits") / lit(args.k))
            .withColumn("hit_rate", (col("hits") > 0).cast("double"))
        )
        result = measured.agg(
            avg("recall").alias("recall_at_k"),
            avg("precision").alias("precision_at_k"),
            avg("hit_rate").alias("hit_rate_at_k"),
            count("customer_id").alias("test_users"),
        ).first()
        print(
            json.dumps(
                {
                    "engine": "Apache Spark",
                    "model": "global_popularity_baseline",
                    "k": args.k,
                    "training_cutoff_inclusive": str(test_start),
                    "test_start_exclusive": str(test_start),
                    "test_end_inclusive": str(cutoff),
                    "test_days": args.test_days,
                    "test_users_with_novel_purchases": result["test_users"],
                    "candidate_items": len(popular),
                    "available": bool(result["test_users"]),
                    "recall_at_k": result["recall_at_k"],
                    "precision_at_k": result["precision_at_k"],
                    "hit_rate_at_k": result["hit_rate_at_k"],
                    "reason": None if result["test_users"] else "No customers had novel purchases in the holdout window.",
                },
                indent=2,
            )
        )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
