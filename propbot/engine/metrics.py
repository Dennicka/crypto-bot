from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class MetricsRegistry:
    """Thin wrapper around Prometheus registry with tag support."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._tags: Dict[str, Iterable[str]] = defaultdict(list)

    def counter(self, name: str, description: str, tags: Iterable[str] | None = None) -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(name, description, tags or (), registry=self.registry)
        return self._counters[name]

    def gauge(self, name: str, description: str, tags: Iterable[str] | None = None) -> Gauge:
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, description, tags or (), registry=self.registry)
        return self._gauges[name]

    def histogram(self, name: str, description: str, tags: Iterable[str] | None = None) -> Histogram:
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, description, tags or (), registry=self.registry)
        return self._histograms[name]

    def increment(self, name: str, labels: Dict[str, str] | None = None, value: float = 1.0) -> None:
        counter = self.counter(name, "auto generated counter", labels.keys() if labels else None)
        counter.labels(**(labels or {})).inc(value)

    def observe(self, name: str, amount: float, labels: Dict[str, str] | None = None) -> None:
        histogram = self.histogram(name, "auto generated histogram", labels.keys() if labels else None)
        histogram.labels(**(labels or {})).observe(amount)

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] | None = None) -> None:
        gauge = self.gauge(name, "auto generated gauge", labels.keys() if labels else None)
        gauge.labels(**(labels or {})).set(value)

    def render(self) -> bytes:
        return generate_latest(self.registry)
