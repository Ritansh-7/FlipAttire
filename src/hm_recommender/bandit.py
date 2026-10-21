
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


ATTRIBUTION_WINDOW = timedelta(days=7)


@dataclass
class BanditArm:
    name: str
    impressions: int = 0
    views: int = 0
    clicks: int = 0
    carts: int = 0
    purchases: int = 0

    @property
    def reward(self) -> float:
        """Weighted event reward: click = 1, purchase = 5."""
        return float(self.clicks + 5 * self.purchases)

    @property
    def ctr(self) -> float:
        """Clicks divided by impressions."""
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def cvr(self) -> float:
        """Purchases divided by impressions, not unique-customer conversion."""
        return self.purchases / self.impressions if self.impressions else 0.0


class MultiArmedBandit:
    """
    Experimental bandit statistics and variant selector.

    Feedback counters are process-local and reset on API restart.
    Actions are counted only when a matching prior product impression
    exists for the same customer and variant within seven days.

    This selector is not used for live recommendation routing.
    """

    def __init__(self, arm_names: list[str] | None = None) -> None:
        if not arm_names:
            arm_names = ["control", "hybrid_v2", "bandit_thompson"]

        self.arms: dict[str, BanditArm] = {
            name: BanditArm(name=name) for name in arm_names
        }

        # (customer_id, variant, article_id) -> impression timestamps
        self.exposures: dict[
            tuple[str, str, str], list[datetime]
        ] = defaultdict(list)

    @staticmethod
    def _utc(value: datetime | None = None) -> datetime:
        timestamp = value or datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)

        return timestamp.astimezone(timezone.utc)

    def record_feedback(
        self,
        variant: str,
        event_type: str,
        customer_id: str | None = None,
        article_id: str | None = None,
        event_time: datetime | None = None,
    ) -> None:
        """Record an impression or an attributable product action."""
        arm = self.arms.setdefault(variant, BanditArm(name=variant))
        timestamp = self._utc(event_time)

        if event_type == "impression":
            arm.impressions += 1

            if customer_id and article_id:
                key = (customer_id, variant, article_id)
                self.exposures[key].append(timestamp)

            return

        if event_type not in {"view", "click", "add_to_cart", "purchase"}:
            return

        # Without customer and product identifiers, attribution is impossible.
        if not customer_id or not article_id:
            return

        key = (customer_id, variant, article_id)
        prior_exposures = self.exposures.get(key, [])

        attributed = any(
            exposure <= timestamp <= exposure + ATTRIBUTION_WINDOW
            for exposure in prior_exposures
        )

        if not attributed:
            return

        if event_type == "view":
            arm.views += 1
        elif event_type == "click":
            arm.clicks += 1
        elif event_type == "add_to_cart":
            arm.carts += 1
        elif event_type == "purchase":
            arm.purchases += 1

    def select_variant(self, epsilon: float = 0.15) -> str:
        """
        Select a variant using epsilon exploration and Beta-distribution
        sampling. This method does not itself enable live routing.
        """
        if not self.arms:
            return "hybrid_v2"

        epsilon = min(1.0, max(0.0, epsilon))

        if random.random() < epsilon:
            return random.choice(list(self.arms.keys()))

        best_variant: str | None = None
        best_sample = -1.0

        for name, arm in self.arms.items():
            alpha = 1 + arm.clicks + (3 * arm.purchases)
            beta = 1 + max(0, arm.impressions - arm.clicks)

            sample = random.betavariate(alpha, beta)

            if sample > best_sample:
                best_sample = sample
                best_variant = name

        return best_variant or next(iter(self.arms))

    def get_stats(self) -> dict:
        total_impressions = sum(
            arm.impressions for arm in self.arms.values()
        )

        return {
            name: {
                "impressions": arm.impressions,
                "views": arm.views,
                "clicks": arm.clicks,
                "carts": arm.carts,
                "purchases": arm.purchases,
                "ctr": round(arm.ctr * 100, 2),
                # Kept for compatibility with existing clients.
                "cvr": round(arm.cvr * 100, 2),
                # Explicit name for the existing CVR definition.
                "purchase_per_impression_pct": round(
                    arm.cvr * 100, 2
                ),
                "traffic_share": round(
                    (arm.impressions / total_impressions) * 100, 1
                ) if total_impressions else 0.0,
            }
            for name, arm in self.arms.items()
        }