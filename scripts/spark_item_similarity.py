"""Build compact item-to-item collaborative candidates with Spark."""

from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import asc, col, collect_set, count, desc, explode, row_number
from pyspark.sql.window import Window


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=Path, default=Path("data/bronze/transactions"))
    parser.add_argument("--output", type=Path, default=Path("models/artifacts/hm_spark_v1.item_similarity.parquet"))
    parser.add_argument("--max-items-per-customer", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--sample-fraction", type=float, default=1.0)
    parser.add_argument("--master", default=None)
    args = parser.parse_args()
    builder = SparkSession.builder.appName("hm-spark-item-similarity")
    if args.master:
        builder = builder.master(args.master)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        tx = spark.read.parquet(str(args.transactions)).select("customer_id", "article_id", "t_dat")
        if args.sample_fraction < 1.0:
            tx = tx.sample(withReplacement=False, fraction=args.sample_fraction, seed=42)
        recent_window = Window.partitionBy("customer_id").orderBy(col("t_dat").desc())
        recent = (tx.withColumn("rn", row_number().over(recent_window)).where(col("rn") <= args.max_items_per_customer)
                  .groupBy("customer_id").agg(collect_set("article_id").alias("items")))
        left = recent.select("customer_id", explode("items").alias("article_id"))
        right = left.select(col("customer_id").alias("right_customer"), col("article_id").alias("right_article"))
        pairs = (left.join(right, left.customer_id == right.right_customer)
                 .where(col("article_id") < col("right_article"))
                 .groupBy("article_id", "right_article").agg(count("*").alias("cooccurrences")))
        both = pairs.select(col("article_id").alias("source_article_id"), col("right_article").alias("similar_article_id"), "cooccurrences").unionByName(
            pairs.select(col("right_article").alias("source_article_id"), col("article_id").alias("similar_article_id"), "cooccurrences"))
        rank_window = Window.partitionBy("source_article_id").orderBy(desc("cooccurrences"), asc("similar_article_id"))
        result = both.withColumn("rn", row_number().over(rank_window)).where(col("rn") <= args.top_k).drop("rn")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.repartition(32, "source_article_id").write.mode("overwrite").parquet(str(args.output))
        print(f"wrote item similarity to {args.output}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

