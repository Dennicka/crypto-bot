from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import Dict

from ..config import VenueConfig


class VenueConnector(ABC):
    """Abstract connector for venue operations."""

    def __init__(self, config: VenueConfig) -> None:
        self.config = config
        self._balances: Dict[str, float] = {"USDT": 10000.0, "BTC": 2.0}

    @abstractmethod
    def refresh_order_book(self) -> Dict[str, float]:
        """Return the best bid/ask for the configured trading pairs."""

    def _simulate_price(self, symbol: str) -> Dict[str, float]:
        base_price = 60000.0 if symbol.startswith("BTC") else 3000.0
        noise = random.uniform(-50.0, 50.0)
        price = base_price + noise + random.uniform(-5, 5)
        spread = random.uniform(0.5, 2.0)
        return {"bid": price - spread, "ask": price + spread}

    def place_order(self, symbol: str, side: str, quantity: float) -> Dict[str, float]:
        book = self.refresh_order_book()
        price = book["bid"] if side == "sell" else book["ask"]
        notional = price * quantity
        fee = notional * (self.config.taker_fee_bps / 10000.0)
        self._balances.setdefault("USDT", 0.0)
        self._balances.setdefault("BTC", 0.0)
        if side == "buy":
            if self._balances["USDT"] < notional + fee:
                raise ValueError("Insufficient balance")
            self._balances["USDT"] -= notional + fee
            self._balances["BTC"] += quantity
        else:
            if self._balances["BTC"] < quantity:
                raise ValueError("Insufficient BTC")
            self._balances["BTC"] -= quantity
            self._balances["USDT"] += notional - fee
        return {
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "fee": fee,
            "timestamp": time.time(),
        }

    def balances(self) -> Dict[str, float]:
        return dict(self._balances)


class SimulatedConnector(VenueConnector):
    """Simulates venues using pseudo-random data."""

    def refresh_order_book(self) -> Dict[str, float]:
        symbol = self.config.trading_pairs[0]
        return self._simulate_price(symbol)
