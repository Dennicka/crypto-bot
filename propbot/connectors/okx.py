from __future__ import annotations

from .base import SimulatedConnector


class OKXConnector(SimulatedConnector):
    """Simulated OKX connector; real implementation would call OKX APIs."""

    venue_name = "okx"
