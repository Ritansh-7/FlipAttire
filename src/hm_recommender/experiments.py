from __future__ import annotations

import hashlib

from .domain import Experiment


class ExperimentService:
    def __init__(self, experiment: Experiment) -> None:
        self.experiment = experiment

    def assign(self, customer_id: str) -> str:
        digest = hashlib.sha256(f"{self.experiment.experiment_id}:{customer_id}".encode()).hexdigest()
        bucket = int(digest[:8], 16) % 10_000
        cumulative = 0
        for variant in self.experiment.variants:
            cumulative += variant.allocation
            if bucket < cumulative:
                return variant.name
        return self.experiment.variants[-1].name

