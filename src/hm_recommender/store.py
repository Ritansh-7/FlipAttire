from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import overload

from .domain import Article, EventType, Experiment, Interaction, StoredEvent


class CustomerIdPool(Sequence[str]):
    def __init__(self, size: int, get_customer_id: Callable[[int], str]) -> None:
        self._size = size
        self._get_customer_id = get_customer_id

    def __len__(self) -> int:
        return self._size

    @overload
    def __getitem__(self, index: int) -> str: ...

    @overload
    def __getitem__(self, index: slice) -> list[str]: ...

    def __getitem__(self, index: int | slice) -> str | list[str]:
        if isinstance(index, slice):
            return [self._get_customer_id(i) for i in range(*index.indices(self._size))]
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("customer ID pool index out of range")
        return self._get_customer_id(index)


class InMemoryStore:
    """Replaceable repository for the first runnable milestone."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.articles: dict[str, Article] = {
            "A001": Article(article_id="A001", product_type="T-shirt", department="Ladies", colour_group="Black", price=19.99),
            "A002": Article(article_id="A002", product_type="Trousers", department="Ladies", colour_group="Blue", price=39.99),
            "A003": Article(article_id="A003", product_type="Jacket", department="Ladies", colour_group="Beige", price=69.99),
            "A004": Article(article_id="A004", product_type="Dress", department="Ladies", colour_group="Black", price=49.99),
            "A005": Article(article_id="A005", product_type="Shirt", department="Menswear", colour_group="White", price=29.99),
            "A006": Article(article_id="A006", product_type="Jeans", department="Menswear", colour_group="Blue", price=44.99),
            "A007": Article(article_id="A007", product_type="Hoodie", department="Menswear", colour_group="Grey", price=34.99),
            "A008": Article(article_id="A008", product_type="Knitwear", department="Ladies", colour_group="Green", price=39.99),
        }
        self.interactions: list[Interaction] = [
            Interaction(customer_id="C001", article_id="A001", event_type=EventType.purchase),
            Interaction(customer_id="C001", article_id="A004", event_type=EventType.view),
            Interaction(customer_id="C002", article_id="A005", event_type=EventType.purchase),
            Interaction(customer_id="C002", article_id="A006", event_type=EventType.purchase),
            Interaction(customer_id="C003", article_id="A003", event_type=EventType.purchase),
        ]
        self.events: list[StoredEvent] = []
        self.experiment = Experiment(
            experiment_id="homepage_recommender_002",
            variants=[
                {"name": "control", "allocation": 5000},
                {"name": "hybrid_v2", "allocation": 5000},
            ],
        )

    @classmethod
    def from_artifacts(cls, articles_path, popularity_path, affinity_path=None, similarity_path=None, history_path=None) -> "InMemoryStore":
        """Load a compact serving snapshot produced by scripts/train_baseline.py."""
        import polars as pl

        def read_parquet(path):
            candidate = Path(path)
            return pl.read_parquet(str(candidate / "**" / "*.parquet") if candidate.is_dir() else path)

        store = cls()
        article_frame = read_parquet(articles_path)
        store.articles = {
            str(row["article_id"]): Article(
                article_id=str(row["article_id"]),
                name=str(row.get("prod_name") or "Fashion item"),
                description=str(row.get("detail_desc") or ""),
                product_type=str(row.get("product_type_name") or "unknown"),
                department=str(row.get("department_name") or "unknown"),
                colour_group=str(row.get("colour_group_name") or "unknown"),
                price=0.0,
                index_group=str(row.get("index_group_name") or "unknown"),
                section=str(row.get("section_name") or "unknown"),
            )
            for row in article_frame.iter_rows(named=True)
        }
        popularity_frame = read_parquet(popularity_path)
        store._popularity_counts = Counter({str(row["article_id"]): int(row["purchases"]) for row in popularity_frame.iter_rows(named=True)})
        store.interactions = []
        # Keep profiles columnar; converting 1.3M customer rows to a Python dict
        # costs several times more memory than the Parquet serving artifact.
        store._customer_department_index = None
        store._item_similarity = defaultdict(list)
        store._customer_history = defaultdict(list)
        if affinity_path:
            candidate = Path(affinity_path)
            affinity_glob = str(candidate / "**" / "*.parquet") if candidate.is_dir() else str(candidate)
            affinity_scan = pl.scan_parquet(affinity_glob)
            affinity_columns = affinity_scan.collect_schema().names()
            required_columns = {"customer_id", "department_name", "interactions"}
            if required_columns.issubset(affinity_columns):
                store._customer_department_index = (
                    affinity_scan.select("customer_id", "department_name", "interactions")
                    .group_by("customer_id")
                    .agg(
                        pl.col("department_name")
                        .sort_by(["interactions", "department_name"])
                        .last()
                        .alias("department_name"),
                        pl.col("interactions").max().alias("interactions"),
                    )
                    .sort("customer_id")
                    .collect(engine="streaming")
                )
        if similarity_path:
            similarity_frame = read_parquet(similarity_path)
            for row in similarity_frame.iter_rows(named=True):
                store._item_similarity[str(row["source_article_id"])].append((str(row["similar_article_id"]), float(row["cooccurrences"])))
        if history_path:
            history_frame = read_parquet(history_path)
            for row in history_frame.sort("t_dat", descending=True).iter_rows(named=True):
                store._customer_history[str(row["customer_id"])].append(str(row["article_id"]))
        return store

    def customer_interactions(self, customer_id: str) -> list[Interaction]:
        return [x for x in self.interactions if x.customer_id == customer_id]

    def popularity(self) -> Counter[str]:
        if hasattr(self, "_popularity_counts"):
            return self._popularity_counts
        return Counter(x.article_id for x in self.interactions if x.event_type == EventType.purchase)

    def customer_departments(self, customer_id: str) -> Counter[str]:
        profile_index = getattr(self, "_customer_department_index", None)
        if profile_index is not None:
            customer_ids = profile_index.get_column("customer_id")
            position = customer_ids.search_sorted(customer_id)
            if position < len(customer_ids) and customer_ids[position] == customer_id:
                department = str(profile_index.item(position, "department_name"))
                interactions = int(profile_index.item(position, "interactions"))
                return Counter({department: interactions})
        if hasattr(self, "_customer_departments") and customer_id in self._customer_departments:
            entry = self._customer_departments[customer_id]
            if isinstance(entry, (list, tuple)):
                return Counter({str(entry[0]): int(entry[1])})
            return Counter(entry)
        return Counter(
            self.articles[x.article_id].department
            for x in self.customer_interactions(customer_id)
            if x.article_id in self.articles
        )

    def customer_id_pool(self) -> Sequence[str]:
        profile_index = getattr(self, "_customer_department_index", None)
        if profile_index is not None:
            customer_ids = profile_index.get_column("customer_id")
            return CustomerIdPool(len(customer_ids), lambda index: str(customer_ids[index]))
        customer_ids = list(getattr(self, "_customer_departments", self.articles).keys())
        return CustomerIdPool(len(customer_ids), customer_ids.__getitem__)

    def similar_items(self, article_id: str) -> list[tuple[str, float]]:
        return getattr(self, "_item_similarity", {}).get(article_id, [])

    def customer_history(self, customer_id: str) -> list[str]:
        return getattr(self, "_customer_history", {}).get(customer_id, [])

    def save_event(self, event: StoredEvent) -> None:
        with self._lock:
            self.events.append(event)
            # Feed live shop activity back into personalization so a customer's
            # views/clicks/carts/purchases shape their next recommendations.
            if event.article_id and event.event_type in {
                EventType.view,
                EventType.click,
                EventType.add_to_cart,
                EventType.purchase,
            }:
                self.interactions.append(
                    Interaction(
                        customer_id=event.customer_id,
                        article_id=event.article_id,
                        event_type=event.event_type,
                        event_time=event.event_time,
                    )
                )

    def hydrate_from_log(self, payloads: list[dict]) -> int:
        """Restore interactions + events from the durable JSONL mirror.

        Keeps per-user personalization alive across API restarts.
        Returns the number of interactions restored.
        """
        restored = 0
        with self._lock:
            seen = {e.event_id for e in self.events}
            for payload in payloads:
                try:
                    event = StoredEvent.model_validate(payload)
                except Exception:
                    continue
                if event.event_id in seen:
                    continue
                seen.add(event.event_id)
                self.events.append(event)
                if event.article_id and event.event_type in {
                    EventType.view,
                    EventType.click,
                    EventType.add_to_cart,
                    EventType.purchase,
                }:
                    self.interactions.append(
                        Interaction(
                            customer_id=event.customer_id,
                            article_id=event.article_id,
                            event_type=event.event_type,
                            event_time=event.event_time,
                        )
                    )
                    restored += 1
        return restored
