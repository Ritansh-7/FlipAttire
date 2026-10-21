from datetime import datetime, timedelta, timezone

import pytest

from hm_recommender.domain import Article, EventType, Experiment, Interaction, StoredEvent, article_category, article_matches_collection
from hm_recommender.experiment_stats import recommendation_experiment_report
from hm_recommender.experiments import ExperimentService
from hm_recommender.recommender import RecommendationService
from hm_recommender.store import InMemoryStore


def make_event(event_id, customer_id, event_type, article_id, variant, event_time):
    return StoredEvent(
        event_id=event_id,
        event_type=event_type,
        customer_id=customer_id,
        article_id=article_id,
        surface="homepage",
        experiment_id="homepage_recommender_002",
        variant=variant,
        event_time=event_time,
    )


def test_assignment_is_stable():
    store = InMemoryStore()
    service = ExperimentService(store.experiment)
    assert store.experiment.experiment_id == "homepage_recommender_002"
    assert [variant.name for variant in store.experiment.variants] == ["control", "hybrid_v2"]
    assert service.assign("C001") == service.assign("C001")


def test_artifact_customer_profiles_are_columnar_and_indexable(tmp_path):
    import polars as pl

    articles_path = tmp_path / "articles.parquet"
    popularity_path = tmp_path / "popularity.parquet"
    affinity_path = tmp_path / "affinity.parquet"
    pl.DataFrame({
        "article_id": ["A1"],
        "prod_name": ["T-shirt"],
        "detail_desc": [""],
        "product_type_name": ["T-shirt"],
        "department_name": ["Ladies"],
        "colour_group_name": ["Blue"],
        "index_group_name": ["Ladieswear"],
        "section_name": ["Ladieswear"],
    }).write_parquet(articles_path)
    pl.DataFrame({"article_id": ["A1"], "purchases": [10]}).write_parquet(popularity_path)
    pl.DataFrame({
        "customer_id": ["C2", "C1", "C1"],
        "department_name": ["Shoes", "Jersey", "Dresses"],
        "interactions": [3, 2, 5],
    }).write_parquet(affinity_path)

    store = InMemoryStore.from_artifacts(articles_path, popularity_path, affinity_path)

    assert store.customer_departments("C1") == {"Dresses": 5}
    assert store.customer_departments("unknown") == {}
    pool = store.customer_id_pool()
    assert len(pool) == 2
    assert pool[0] == "C1"
    assert pool[-1] == "C2"
    assert not hasattr(store, "_customer_departments")


def test_experiment_rejects_invalid_variant_allocations():
    with pytest.raises(ValueError, match="sum to 10000"):
        Experiment(
            experiment_id="invalid",
            variants=[{"name": "control", "allocation": 4_000}, {"name": "treatment", "allocation": 4_000}],
        )


@pytest.mark.parametrize("index_group", ["Ladieswear", "Menswear"])
def test_beauty_collection_is_gender_neutral_and_excludes_clothing(index_group):
    beauty_item = Article(
        article_id=f"beauty-{index_group}",
        product_type="Fine cosmetics",
        department="Take Care External",
        colour_group="unknown",
        price=0,
        index_group=index_group,
    )
    clothing_item = Article(
        article_id=f"clothes-{index_group}",
        product_type="Blouse",
        department="Take Care External",
        colour_group="unknown",
        price=0,
        index_group=index_group,
    )

    assert article_matches_collection(beauty_item, "BEAUTY")
    assert not article_matches_collection(clothing_item, "BEAUTY")


@pytest.mark.parametrize("index_group", ["Ladieswear", "Menswear"])
def test_beauty_collection_includes_unisex_fragrance(index_group):
    perfume = Article(
        article_id=f"perfume-{index_group}",
        name="Studio perfume",
        description="A subtle scent for everyone.",
        product_type="Other accessories",
        department="Studio Collection",
        colour_group="unknown",
        price=0,
        index_group=index_group,
    )

    assert article_matches_collection(perfume, "BEAUTY")


def test_beauty_collection_excludes_kids_cosmetics_and_cosmetic_bags():
    kids_cosmetics = Article(
        article_id="kids-cosmetics",
        name="Lip balm unicorn",
        product_type="Fine cosmetics",
        department="Girls Small Acc/Bags",
        colour_group="unknown",
        price=0,
        index_group="Baby/Children",
    )
    cosmetic_bag = Article(
        article_id="cosmetic-bag",
        name="Bobby Lipstickbag",
        description="Small bag for lipstick.",
        product_type="Bag",
        department="Other accessories",
        colour_group="unknown",
        price=0,
        index_group="Ladieswear",
    )

    assert not article_matches_collection(kids_cosmetics, "BEAUTY")
    assert not article_matches_collection(cosmetic_bag, "BEAUTY")


def test_studio_collection_excludes_premium_quality_shoes():
    premium_shoe = Article(
        article_id="premium-shoe",
        product_type="Sneakers",
        department="Premium Quality",
        colour_group="unknown",
        price=0,
        index_group="Ladieswear",
        section="Womens Shoes",
    )
    studio_piece = Article(
        article_id="studio-piece",
        product_type="Dress",
        department="Conscious Exclusive",
        colour_group="unknown",
        price=0,
        index_group="Ladieswear",
        section="Special Collections",
    )

    assert not article_matches_collection(premium_shoe, "STUDIO")
    assert article_matches_collection(studio_piece, "STUDIO")


def test_socks_are_not_counted_as_shoes():
    socks = Article(
        article_id="socks",
        product_type="Socks",
        department="Womens Socks",
        colour_group="unknown",
        price=0,
    )
    sneakers = Article(
        article_id="sneakers",
        product_type="Sneakers",
        department="Womens Shoes",
        colour_group="unknown",
        price=0,
    )

    assert article_category(socks) == "Accessories"
    assert article_category(sneakers) == "Shoes"


def test_experiment_report_attributes_only_exposed_products_within_window():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        make_event("e1", "C1", EventType.impression, "A1", "control", start),
        make_event("e2", "C1", EventType.impression, "A2", "control", start),
        make_event("e3", "C1", EventType.click, "A1", "control", start + timedelta(hours=1)),
        make_event("e4", "C1", EventType.view, "A1", "control", start + timedelta(hours=1)),
        make_event("e5", "C1", EventType.add_to_cart, "A1", "control", start + timedelta(hours=2)),
        make_event("e6", "C1", EventType.purchase, "A1", "control", start + timedelta(days=1)),
        make_event("e7", "C1", EventType.purchase, "UNEXPOSED", "control", start + timedelta(days=1)),
        make_event("e8", "C1", EventType.purchase, "A1", "hybrid_v2", start + timedelta(days=1)),
        make_event("e9", "C1", EventType.purchase, "A2", "control", start - timedelta(hours=1)),
        make_event("e10", "C2", EventType.impression, "A1", "hybrid_v2", start),
        make_event("e11", "C2", EventType.purchase, "A1", "hybrid_v2", start + timedelta(days=8)),
    ]

    report = recommendation_experiment_report(events, "homepage_recommender_002")
    metrics = {metric["variant"]: metric for metric in report["variants"]}

    assert report["attribution_window_days"] == 7
    assert metrics["control"]["exposed_users"] == 1
    assert metrics["control"]["impression_events"] == 2
    assert metrics["control"]["product_viewers"] == 1
    assert metrics["control"]["clickers"] == 1
    assert metrics["control"]["cart_users"] == 1
    assert metrics["control"]["converters"] == 1
    assert metrics["control"]["conversion_rate"] == 1.0
    assert metrics["hybrid_v2"]["converters"] == 0
    assert report["treatment_vs_control"]["p_value"] is None


def test_experiment_inference_excludes_customers_exposed_to_multiple_variants():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        make_event("c1-control", "C1", EventType.impression, "A1", "control", start),
        make_event("c1-purchase", "C1", EventType.purchase, "A1", "control", start + timedelta(hours=1)),
        make_event("c2-treatment", "C2", EventType.impression, "A2", "hybrid_v2", start),
        make_event("c2-purchase", "C2", EventType.purchase, "A2", "hybrid_v2", start + timedelta(hours=1)),
        make_event("c3-control", "C3", EventType.impression, "A3", "control", start),
        make_event("c3-treatment", "C3", EventType.impression, "A4", "hybrid_v2", start),
        make_event("c3-purchase", "C3", EventType.purchase, "A3", "control", start + timedelta(hours=1)),
    ]

    report = recommendation_experiment_report(events, "homepage_recommender_002")
    comparison = report["treatment_vs_control"]

    assert report["customers_exposed_to_multiple_variants"] == 1
    assert comparison["analysis_population"] == "customers exposed to exactly one variant"
    assert comparison["control_exposed_users"] == 1
    assert comparison["treatment_exposed_users"] == 1
    assert comparison["excluded_cross_variant_customers"] == 1


def test_experiment_inference_is_not_reported_for_multiple_treatment_arms():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        make_event("control", "C1", EventType.impression, "A1", "control", start),
        make_event("treatment-a", "C2", EventType.impression, "A2", "hybrid_v2", start),
        make_event("treatment-b", "C3", EventType.impression, "A3", "bandit", start),
    ]

    report = recommendation_experiment_report(events, "homepage_recommender_002")

    assert report["treatment_vs_control"]["p_value"] is None
    assert "multiple treatment variants" in report["treatment_vs_control"]["reason"]


def test_recommendations_exclude_purchases_and_are_diverse():
    store = InMemoryStore()
    service = RecommendationService(store, ExperimentService(store.experiment))
    result = service.recommend("C001", "homepage", 5)
    ids = [item.article_id for item in result.recommendations]
    assert "A001" not in ids
    assert len(ids) == len(set(ids))


def test_hybrid_recommendations_use_recent_feedback_and_log_scaled_affinity():
    store = InMemoryStore()
    store.articles = {
        "old-purchase": Article(article_id="old-purchase", product_type="Jacket", department="Menswear", colour_group="Red", price=0, available=False),
        "recent-click": Article(article_id="recent-click", product_type="T-shirt", department="Ladies", colour_group="Blue", price=0, available=False),
        "popular-mens": Article(article_id="popular-mens", product_type="Shirt", department="Menswear", colour_group="Black", price=0),
        "recent-womens": Article(article_id="recent-womens", product_type="T-shirt", department="Ladies", colour_group="Blue", price=0),
    }
    store._popularity_counts = {"popular-mens": 500}
    store._customer_departments = {"hybrid-shopper": ["Ladies", 50_000]}
    store.interactions = [
        Interaction(
            customer_id="hybrid-shopper",
            article_id="old-purchase",
            event_type=EventType.purchase,
            event_time=datetime.now(timezone.utc) - timedelta(days=90),
        ),
        Interaction(
            customer_id="hybrid-shopper",
            article_id="recent-click",
            event_type=EventType.click,
            event_time=datetime.now(timezone.utc),
        ),
    ]
    service = RecommendationService(store, ExperimentService(store.experiment))
    if service.experiments.assign("hybrid-shopper") != "hybrid_v2":
        customer_id = next(
            f"hybrid-shopper-{index}"
            for index in range(10_000)
            if service.experiments.assign(f"hybrid-shopper-{index}") == "hybrid_v2"
        )
        store._customer_departments[customer_id] = ["Ladies", 50_000]
        store.interactions = [
            Interaction(
                customer_id=customer_id,
                article_id=interaction.article_id,
                event_type=interaction.event_type,
                event_time=interaction.event_time,
            )
            for interaction in store.interactions
        ]
    else:
        customer_id = "hybrid-shopper"

    result = service.recommend(customer_id, "homepage", 5)

    assert result.variant == "hybrid_v2"
    assert result.experiment_id == "homepage_recommender_002"
    assert result.model_version == "hybrid_v2"
    assert result.recommendations[0].article_id == "recent-womens"
    assert "old-purchase" not in {item.article_id for item in result.recommendations}


def test_control_recommendations_remain_popularity_ranked():
    store = InMemoryStore()
    store.articles = {
        "womens-item": Article(article_id="womens-item", product_type="T-shirt", department="Ladies", colour_group="Blue", price=0),
        "mens-item": Article(article_id="mens-item", product_type="Shirt", department="Menswear", colour_group="Black", price=0),
    }
    store._popularity_counts = {"womens-item": 2, "mens-item": 100}
    service = RecommendationService(store, ExperimentService(store.experiment))
    customer_id = next(
        f"control-shopper-{index}"
        for index in range(10_000)
        if service.experiments.assign(f"control-shopper-{index}") == "control"
    )

    result = service.recommend(customer_id, "homepage", 2)

    assert result.variant == "control"
    assert result.model_version == "popularity_v1"
    assert [item.article_id for item in result.recommendations] == ["mens-item", "womens-item"]



def test_bandit_router():
    from datetime import datetime, timedelta, timezone

    from hm_recommender.bandit import MultiArmedBandit

    bandit = MultiArmedBandit()
    now = datetime.now(timezone.utc)

    # Record a product impression first.
    bandit.record_feedback(
        "hybrid_v2", "impression",
        customer_id="customer_1",
        article_id="product_1",
        event_time=now,
    )

    # Matching product actions should be attributed.
    for event_type in ("view", "click", "add_to_cart", "purchase"):
        bandit.record_feedback(
            "hybrid_v2", event_type,
            customer_id="customer_1",
            article_id="product_1",
            event_time=now + timedelta(minutes=1),
        )

    stats = bandit.get_stats()
    arm = stats["hybrid_v2"]

    assert arm["impressions"] == 1
    assert arm["views"] == 1
    assert arm["clicks"] == 1
    assert arm["carts"] == 1
    assert arm["purchases"] == 1
    assert arm["ctr"] == 100.0
    assert arm["cvr"] == 100.0

    # An action without a matching exposure must not count.
    bandit.record_feedback(
        "hybrid_v2", "purchase",
        customer_id="customer_2",
        article_id="product_1",
        event_time=now + timedelta(minutes=2),
    )
    assert bandit.get_stats()["hybrid_v2"]["purchases"] == 1

    # An action outside the seven-day attribution window must not count.
    bandit.record_feedback(
        "hybrid_v2", "purchase",
        customer_id="customer_1",
        article_id="product_1",
        event_time=now + timedelta(days=7, seconds=1),
    )
    assert bandit.get_stats()["hybrid_v2"]["purchases"] == 1


def test_evaluations_metrics():
    from hm_recommender.evaluations import compute_eval_metrics
    store = InMemoryStore()
    evals = compute_eval_metrics(store, store.events)
    assert evals["available"] is False
    assert evals["evaluation_mode"] == "offline_holdout_required"
    assert "spark_evaluate.py" in evals["reason"]
