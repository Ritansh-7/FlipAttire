from __future__ import annotations

import json
import os
from typing import Any


class EventBus:
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


class NoopEventBus(EventBus):
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        return None


class KafkaEventBus(EventBus):
    def __init__(self, bootstrap_servers: str) -> None:
        import threading

        from confluent_kafka import Producer

        self._producer = Producer({"bootstrap.servers": bootstrap_servers})
        self._errors = 0
        # Background flush: guarantees buffered events reach the broker within
        # ~2s without adding latency to API requests. produce()+poll(0) alone
        # can leave recent events sitting in the local buffer (invisible in
        # Redpanda Console) until the next request triggers a poll.
        worker = threading.Thread(target=self._flush_loop, name="kafka-flush", daemon=True)
        worker.start()

    def _flush_loop(self) -> None:
        import time

        while True:
            time.sleep(2)
            try:
                self._producer.flush(1)
            except Exception:
                pass

    def _delivered(self, error, _message) -> None:
        if error is not None:
            self._errors += 1
            print(f"kafka delivery failed ({self._errors} total): {error}")

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        try:
            self._producer.produce(topic, json.dumps(payload, default=str).encode("utf-8"), callback=self._delivered)
        except BufferError:
            # Queue full (broker down): drop + poll to make room, never break the API.
            self._errors += 1
            print(f"kafka queue full, event dropped ({self._errors} total)")
        self._producer.poll(0)


def build_event_bus() -> EventBus:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        return NoopEventBus()
    try:
        return KafkaEventBus(bootstrap_servers)
    except ImportError:
        return NoopEventBus()

