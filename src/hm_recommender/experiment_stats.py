from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta, timezone

from .domain import EventType, StoredEvent

ATTRIBUTION_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class VariantMetric:
    variant: str
    exposed_users: int
    impression_events: int
    viewers: int
    clickers: int
    cart_users: int
    converters: int

    @property
    def click_through_rate(self) -> float:
        return self.clickers / self.exposed_users if self.exposed_users else 0.0

    @property
    def product_view_rate(self) -> float:
        return self.viewers / self.exposed_users if self.exposed_users else 0.0

    @property
    def add_to_cart_rate(self) -> float:
        return self.cart_users / self.exposed_users if self.exposed_users else 0.0

    @property
    def conversion_rate(self) -> float:
        return self.converters / self.exposed_users if self.exposed_users else 0.0


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def two_proportion_test(control: VariantMetric, treatment: VariantMetric) -> dict[str, float | None]:
    if not control.exposed_users or not treatment.exposed_users:
        return {"absolute_lift": None, "relative_lift": None, "z_score": None, "p_value": None}
    pooled = (control.converters + treatment.converters) / (control.exposed_users + treatment.exposed_users)
    expected = (
        pooled * control.exposed_users,
        (1 - pooled) * control.exposed_users,
        pooled * treatment.exposed_users,
        (1 - pooled) * treatment.exposed_users,
    )
    absolute_lift = treatment.conversion_rate - control.conversion_rate
    relative_lift = ((treatment.conversion_rate / control.conversion_rate) - 1) if control.conversion_rate else None
    if min(expected) < 5:
        return {
            "absolute_lift": absolute_lift,
            "relative_lift": relative_lift,
            "z_score": None,
            "p_value": None,
        }
    standard_error = math.sqrt(pooled * (1 - pooled) * (1 / control.exposed_users + 1 / treatment.exposed_users))
    if standard_error == 0:
        return {"absolute_lift": absolute_lift, "relative_lift": relative_lift, "z_score": None, "p_value": None}
    z_score = (treatment.conversion_rate - control.conversion_rate) / standard_error
    p_value = 2 * (1 - _normal_cdf(abs(z_score)))
    return {
        "absolute_lift": absolute_lift,
        "relative_lift": relative_lift,
        "z_score": z_score,
        "p_value": p_value,
    }


def recommendation_experiment_report(events: list[StoredEvent], experiment_id: str) -> dict:
    relevant = [event for event in events if event.experiment_id == experiment_id]
    exposed_users: dict[str, set[str]] = defaultdict(set)
    exposures: dict[tuple[str, str, str], list] = defaultdict(list)
    impression_counts: Counter[str] = Counter()
    attributed_users: dict[str, dict[EventType, set[str]]] = defaultdict(
        lambda: {
            EventType.click: set(),
            EventType.view: set(),
            EventType.add_to_cart: set(),
            EventType.purchase: set(),
        }
    )

    def utc(event: StoredEvent):
        value = event.event_time
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    for event in relevant:
        if not event.variant:
            continue
        if event.event_type == EventType.impression and event.article_id:
            exposed_users[event.variant].add(event.customer_id)
            impression_counts[event.variant] += 1
            exposures[(event.customer_id, event.variant, event.article_id)].append(utc(event))

    action_types = {
        EventType.view: EventType.view,
        EventType.click: EventType.click,
        EventType.add_to_cart: EventType.add_to_cart,
        EventType.purchase: EventType.purchase,
    }
    for event in relevant:
        action_type = action_types.get(event.event_type)
        if not action_type or not event.variant or not event.article_id:
            continue
        action_time = utc(event)
        prior_exposures = exposures.get((event.customer_id, event.variant, event.article_id), [])
        if any(exposure_time <= action_time <= exposure_time + ATTRIBUTION_WINDOW for exposure_time in prior_exposures):
            attributed_users[event.variant][action_type].add(event.customer_id)

    variants = sorted(exposed_users)
    variants_by_user: dict[str, set[str]] = defaultdict(set)
    for variant, users in exposed_users.items():
        for user in users:
            variants_by_user[user].add(variant)
    cross_variant_users = {
        user for user, user_variants in variants_by_user.items() if len(user_variants) > 1
    }
    metrics = []
    for variant in variants:
        metric = VariantMetric(
            variant=variant,
            exposed_users=len(exposed_users[variant]),
            impression_events=impression_counts[variant],
            viewers=len(attributed_users[variant][EventType.view]),
            clickers=len(attributed_users[variant][EventType.click]),
            cart_users=len(attributed_users[variant][EventType.add_to_cart]),
            converters=len(attributed_users[variant][EventType.purchase]),
        )
        metrics.append(
            {
                "variant": metric.variant,
                "exposed_users": metric.exposed_users,
                "impression_events": metric.impression_events,
                "product_viewers": metric.viewers,
                "product_view_rate": metric.product_view_rate,
                "clickers": metric.clickers,
                "click_through_rate": metric.click_through_rate,
                "cart_users": metric.cart_users,
                "add_to_cart_rate": metric.add_to_cart_rate,
                "converters": metric.converters,
                "conversion_rate": metric.conversion_rate,
            }
        )
    result: dict = {
        "experiment_id": experiment_id,
        "attribution_window_days": ATTRIBUTION_WINDOW.days,
        "p_value_method": "two-sided pooled two-proportion z-test; shown only when each expected cell count is at least 5",
        "customers_exposed_to_multiple_variants": len(cross_variant_users),
        "variants": metrics,
    }
    control = next((metric for metric in metrics if metric["variant"] == "control"), None)
    treatment = next((metric for metric in metrics if metric["variant"] != "control"), None)
    if control and treatment and len(variants) == 2:
        control_users = exposed_users["control"] - cross_variant_users
        treatment_users = exposed_users[treatment["variant"]] - cross_variant_users
        result["treatment_vs_control"] = {
            **two_proportion_test(
                VariantMetric(
                    variant=control["variant"],
                    exposed_users=len(control_users),
                    impression_events=control["impression_events"],
                    viewers=control["product_viewers"],
                    clickers=control["clickers"],
                    cart_users=control["cart_users"],
                    converters=len(attributed_users["control"][EventType.purchase] - cross_variant_users),
                ),
                VariantMetric(
                    variant=treatment["variant"],
                    exposed_users=len(treatment_users),
                    impression_events=treatment["impression_events"],
                    viewers=treatment["product_viewers"],
                    clickers=treatment["clickers"],
                    cart_users=treatment["cart_users"],
                    converters=len(attributed_users[treatment["variant"]][EventType.purchase] - cross_variant_users),
                ),
            ),
            "analysis_population": "customers exposed to exactly one variant",
            "control_exposed_users": len(control_users),
            "treatment_exposed_users": len(treatment_users),
            "excluded_cross_variant_customers": len(cross_variant_users),
        }
    elif control and len(variants) > 2:
        result["treatment_vs_control"] = {
            "absolute_lift": None,
            "relative_lift": None,
            "z_score": None,
            "p_value": None,
            "reason": "pairwise inference is disabled when an experiment has multiple treatment variants",
        }
    return result
