from __future__ import annotations

import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

from ..config import VenueConfig


@dataclass
class OrderBookLevel:
    bid: float
    ask: float
    timestamp: float


class VenueConnector(ABC):
    """Connector abstraction shared by real and simulated venues."""

    def __init__(self, config: VenueConfig) -> None:
        self.config = config
        self._books: Dict[str, OrderBookLevel] = {}
        self._balances: Dict[str, float] = {}
        self._last_refresh: float = 0.0

    @abstractmethod
    def refresh_order_books(self) -> Mapping[str, OrderBookLevel]:
        """Retrieve best bid/ask for all configured trading pairs."""

    @abstractmethod
    def place_order(self, *, symbol: str, side: str, quantity: float) -> Dict[str, float]:
        """Submit an order on the venue and return order metadata."""

    @abstractmethod
    def cancel_order(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        """Cancel an existing order."""

    @abstractmethod
    def order_status(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        """Fetch the order status for the given identifier."""

    @abstractmethod
    def balances(self) -> Mapping[str, float]:
        """Return balances (free + locked) for the venue."""

    def symbol_for_exchange(self, symbol: str) -> str:
        """Map an internal symbol to the venue representation."""
        overrides = self.config.symbol_overrides
        if symbol in overrides:
            return overrides[symbol]
        return symbol.replace("/", "").upper()

    def quantize_price(self, price: float) -> float:
        precision = max(self.config.price_precision, 0)
        step = 10 ** (-precision)
        return math.floor(price / step) * step

    def quantize_quantity(self, quantity: float) -> float:
        precision = max(self.config.quantity_precision, 0)
        step = 10 ** (-precision)
        quantized = math.floor(quantity / step) * step
        return max(quantized, self.config.min_qty)

    def best_book(self, symbol: str) -> OrderBookLevel | None:
        return self._books.get(symbol)

    def update_cached_books(self, books: Mapping[str, OrderBookLevel]) -> None:
        self._books.update(books)
        self._last_refresh = time.time()

    def cached_books(self) -> Mapping[str, OrderBookLevel]:
        if not self._books or time.time() - self._last_refresh > 5:
            return {}
        return dict(self._books)


class SimulatedConnector(VenueConnector):
    """Simulated connector used for paper trading and unit tests."""

    def __init__(self, config: VenueConfig) -> None:
        super().__init__(config)
        self._balances = {"USDT": 10000.0, "BTC": 2.5, "ETH": 25.0}

    def refresh_order_books(self) -> Mapping[str, OrderBookLevel]:
        books: Dict[str, OrderBookLevel] = {}
        now = time.time()
        for pair in self.config.trading_pairs:
            base = 60000.0 if pair.startswith("BTC") else 3200.0
            noise = random.uniform(-150.0, 150.0)
            mid = base + noise
            spread = random.uniform(1.0, 4.0)
            books[pair] = OrderBookLevel(bid=mid - spread, ask=mid + spread, timestamp=now)
        self.update_cached_books(books)
        return books

    def place_order(self, *, symbol: str, side: str, quantity: float) -> Dict[str, float]:
        books = self.cached_books() or self.refresh_order_books()
        book = books[symbol]
        price = book.ask if side.lower() == "buy" else book.bid
        price = self.quantize_price(price)
        qty = self.quantize_quantity(quantity)
        notional = price * qty
        fee_rate = self.config.taker_fee_bps / 10000.0
        fee = notional * fee_rate
        base, quote = symbol.split("/")
        self._balances.setdefault(base, 0.0)
        self._balances.setdefault(quote, 0.0)
        if side.lower() == "buy":
            if self._balances[quote] < notional + fee:
                raise ValueError("insufficient quote balance")
            self._balances[quote] -= notional + fee
            self._balances[base] += qty
        else:
            if self._balances[base] < qty:
                raise ValueError("insufficient base balance")
            self._balances[base] -= qty
            self._balances[quote] += notional - fee
        return {
            "orderId": f"sim-{int(time.time() * 1000)}",
            "symbol": symbol,
            "side": side,
            "price": price,
            "executedQty": qty,
            "status": "FILLED",
            "fee": fee,
            "timestamp": time.time(),
        }

    def cancel_order(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        return {"symbol": symbol, "orderId": order_id, "status": "CANCELED"}

    def order_status(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        return {"symbol": symbol, "orderId": order_id, "status": "FILLED"}

    def balances(self) -> Mapping[str, float]:
        return dict(self._balances)

    def seed_balances(self, balances: Mapping[str, float]) -> None:
        self._balances.update(dict(balances))


def merge_balances(*balance_maps: Mapping[str, float]) -> Dict[str, float]:
    merged: Dict[str, float] = {}
    for balances in balance_maps:
        for asset, amount in balances.items():
            merged[asset] = merged.get(asset, 0.0) + amount
    return merged


def ensure_pairs_exist(connector: VenueConnector, pairs: Iterable[str]) -> None:
    missing = [pair for pair in pairs if connector.best_book(pair) is None]
    if missing:
        connector.refresh_order_books()
