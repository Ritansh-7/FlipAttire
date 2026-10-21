"""Train H&M popularity and customer-affinity retrieval artifacts with Spark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, desc, max as spark_max, row_number
from pyspark.sql.window import Window


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=Path, default=Path("data/bronze/transactions"))
    parser.add_argument("--articles", type=Path, default=Path("data/bronze/articles.parquet"))
    parser.add_argument("--output", type=Path, default=Path("models/artifacts/hm_spark_v1"))
    parser.add_argument("--master", default=None)
    args = parser.parse_args()

    builder = SparkSession.builder.appName("hm-spark-train")
    if args.master:
        builder = builder.master(args.master)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        tx = spark.read.parquet(str(args.transactions)).select(
            col("customer_id").cast("string"), col("article_id").cast("string"), col("t_dat")
        )
        articles = spark.read.parquet(str(args.articles)).select(
            col("article_id").cast("string"), "product_type_name", "department_name", "colour_group_name"
        )
        cutoff = tx.select(spark_max("t_dat").alias("max_date")).first()["max_date"]
        if cutoff is None:
            raise ValueError("cannot train recommendation artifacts from an empty transaction dataset")
        train = tx
        popularity = train.groupBy("article_id").agg(count("*").alias("purchases"), spark_max("t_dat").alias("last_seen")).orderBy(desc("purchases"), desc("last_seen"))
        affinity = (
            train.join(articles, "article_id")
            .groupBy("customer_id", "department_name")
            .agg(count("*").alias("interactions"))
        )
        window = Window.partitionBy("customer_id").orderBy(desc("interactions"))
        top_affinity = affinity.withColumn("rn", row_number().over(window)).where(col("rn") <= 3).drop("rn")
        recent_window = Window.partitionBy("customer_id").orderBy(col("t_dat").desc())
        recent_items = tx.withColumn("rn", row_number().over(recent_window)).where(col("rn") <= 5).select("customer_id", "article_id", "t_dat")

        output = args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        popularity.write.mode("overwrite").parquet(str(output.with_suffix(".popularity.parquet")))
        # Keep the full affinity aggregation in Spark's execution plan, but only
        # persist the compact top-3 serving snapshot. This avoids a needless
        # 12M-row artifact and keeps local Windows runs memory-safe.
        top_affinity.repartition(32, "customer_id").write.mode("overwrite").parquet(str(output.with_suffix(".customer_top_affinity.parquet")))
        recent_items.repartition(32, "customer_id").write.mode("overwrite").parquet(str(output.with_suffix(".customer_recent_items.parquet")))
        metadata = {"model_version": output.stem, "training_cutoff": str(cutoff), "fit_scope": "all_available_transactions", "engine": "Apache Spark", "persisted_affinity": "top_3_per_customer", "persisted_history": "top_5_per_customer"}
        output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
