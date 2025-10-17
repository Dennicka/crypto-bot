from __future__ import annotations

from .base import SimulatedConnector


class BinanceConnector(SimulatedConnector):
    """Simulated Binance connector; real implementation would call Binance APIs."""

    venue_name = "binance"
