from __future__ import annotations

import itertools
import time
from typing import Dict, Iterable, List, Optional

from ..config import AppConfig, VenueConfig
from ..connectors.base import SimulatedConnector, VenueConnector
from ..connectors.binance import BinanceConnector, BinanceSimulatedConnector
from ..connectors.okx import OKXConnector, OKXSimulatedConnector
from ..engine.metrics import MetricsRegistry
from ..engine.state import ControlState, EngineState, ExecutionRecord, Opportunity
from ..storage import Journal

CONNECTOR_FACTORIES: Dict[str, type[VenueConnector]] = {
    "binance": BinanceConnector,
    "okx": OKXConnector,
}

SIMULATED_FACTORIES: Dict[str, type[SimulatedConnector]] = {
    "binance": BinanceSimulatedConnector,
    "okx": OKXSimulatedConnector,
}


class ArbitrageEngine:
    """Evaluate opportunities and route executions across venues."""

    def __init__(
        self,
        *,
        config: AppConfig,
        metrics: MetricsRegistry,
        journal: Journal,
        state: EngineState,
        control_state: ControlState,
    ) -> None:
        self.config = config
        self.metrics = metrics
        self.journal = journal
        self.state = state
        self.control_state = control_state
        self._connectors: Dict[str, VenueConnector] = {}
        self._last_execution_ts: float = 0.0
        self._runtime_min_spread = config.engine.min_spread_bps
        self._runtime_default_notional = config.engine.default_notional_usd
        self._cooldown_seconds = config.engine.cooldown_ms / 1000.0
        self._safety_margin = config.engine.safety_margin_bps
        self._venue_by_name: Dict[str, VenueConfig] = {venue.name: venue for venue in config.venue_list}

        for venue in config.venue_list:
            connector = self._build_connector(venue)
            self._connectors[venue.name] = connector
        if config.safe_mode.hold_on_startup:
            self.control_state.hold("SAFE_MODE_STARTUP")

    # ------------------------------------------------------------------
    def _build_connector(self, venue: VenueConfig) -> VenueConnector:
        venue_key = venue.name.lower()
        if venue.simulate:
            factory = SIMULATED_FACTORIES.get(venue_key, SimulatedConnector)
            return factory(venue)
        factory = CONNECTOR_FACTORIES.get(venue_key)
        if factory is None:
            raise ValueError(f"Unsupported venue: {venue.name}")
        return factory(venue, profile=self.config.mode)

    # ------------------------------------------------------------------
    def poll_market_data(self) -> None:
        for venue in self.config.venue_list:
            connector = self._connectors[venue.name]
            try:
                books = connector.refresh_order_books()
            except Exception as exc:  # pragma: no cover - network dependent
                self.metrics.increment("order_book_error_total", {"venue": venue.name, "error": str(exc)})
                continue
            serialized = {
                pair: {"bid": level.bid, "ask": level.ask, "timestamp": level.timestamp}
                for pair, level in books.items()
            }
            self.state.order_books[venue.name] = serialized
            for pair, level in books.items():
                self.metrics.observe(
                    "order_book_spread_bps",
                    amount=(level.ask - level.bid) / max(level.ask, 1e-9) * 10000,
                    labels={"venue": venue.name, "symbol": pair},
                )

    # ------------------------------------------------------------------
    def evaluate(self) -> None:
        if self.control_state.is_hold:
            return
        opportunities = self._find_opportunities()
        for opp in opportunities:
            self.state.record_opportunity(opp)
            self.metrics.observe("spread_bps", opp.spread_bps, {"symbol": opp.symbol})
            executed = self._execute_if_allowed(opp)
            record = ExecutionRecord(opportunity=opp, executed=executed, reason="")
            self.state.record_execution(record)
            self._journal_opportunity(opp, executed)
        self._update_unrealized_pnl()

    def _journal_opportunity(self, opportunity: Opportunity, executed: bool) -> None:
        payload = {
            "timestamp": opportunity.timestamp,
            "symbol": opportunity.symbol,
            "buy_venue": opportunity.buy_venue,
            "sell_venue": opportunity.sell_venue,
            "spread_bps": opportunity.spread_bps,
            "notional": opportunity.notional,
            "executed": executed,
        }
        self.journal.record_event("opportunity", payload)

    def _find_opportunities(self) -> List[Opportunity]:
        if len(self.state.order_books) < 2:
            return []
        timestamp = time.time()
        opportunities: List[Opportunity] = []
        venue_pairs = list(self.state.order_books.items())
        symbols = self._shared_symbols()
        for (buy_name, buy_books), (sell_name, sell_books) in itertools.permutations(venue_pairs, 2):
            buy_config = self._venue_by_name.get(buy_name)
            sell_config = self._venue_by_name.get(sell_name)
            if not buy_config or not sell_config:
                continue
            total_fee_bps = buy_config.taker_fee_bps + sell_config.taker_fee_bps
            threshold = max(self._runtime_min_spread, total_fee_bps + self._safety_margin)
            for symbol in symbols:
                buy_book = buy_books.get(symbol)
                sell_book = sell_books.get(symbol)
                if not buy_book or not sell_book:
                    continue
                buy_price = buy_book["ask"]
                sell_price = sell_book["bid"]
                spread = (sell_price - buy_price) / max(buy_price, 1e-9) * 10000
                if spread <= threshold:
                    continue
                opportunities.append(
                    Opportunity(
                        symbol=symbol,
                        buy_venue=buy_name,
                        sell_venue=sell_name,
                        spread_bps=spread,
                        notional=self._runtime_default_notional,
                        timestamp=timestamp,
                    )
                )
        opportunities.sort(key=lambda opp: opp.spread_bps, reverse=True)
        return opportunities

    def _shared_symbols(self) -> Iterable[str]:
        shared: Optional[set[str]] = None
        for venue in self.config.venue_list:
            symbols = set(venue.trading_pairs)
            if shared is None:
                shared = symbols
            else:
                shared &= symbols
        return shared or []

    def _execute_if_allowed(self, opportunity: Opportunity) -> bool:
        now = time.time()
        if self.control_state.safe_mode_enabled:
            return False
        if now - self._last_execution_ts < self._cooldown_seconds:
            return False
        try:
            executed = self._perform_execution(opportunity)
        except Exception as exc:  # pragma: no cover - network dependent
            self.metrics.increment("execution_rejected_total", {"reason": str(exc)})
            self.journal.record_event(
                "execution_error",
                {
                    "timestamp": time.time(),
                    "symbol": opportunity.symbol,
                    "buy_venue": opportunity.buy_venue,
                    "sell_venue": opportunity.sell_venue,
                    "error": str(exc),
                },
            )
            return False
        if executed:
            self._last_execution_ts = now
        return executed

    def _perform_execution(self, opportunity: Opportunity) -> bool:
        buy_connector = self._connectors[opportunity.buy_venue]
        sell_connector = self._connectors[opportunity.sell_venue]
        buy_config = self._venue_by_name[opportunity.buy_venue]
        sell_config = self._venue_by_name[opportunity.sell_venue]
        buy_books = self.state.order_books.get(opportunity.buy_venue, {})
        book = buy_books.get(opportunity.symbol)
        if not book:
            return False
        ask_price = book["ask"]
        quantity = max(opportunity.notional / max(ask_price, 1e-9), buy_config.min_qty)
        quantity = buy_connector.quantize_quantity(quantity)
        buy_order = buy_connector.place_order(symbol=opportunity.symbol, side="buy", quantity=quantity)
        sell_order = sell_connector.place_order(symbol=opportunity.symbol, side="sell", quantity=quantity)
        buy_price = float(buy_order.get("price", ask_price))
        sell_price = float(sell_order.get("price", ask_price))
        buy_fee = buy_price * quantity * (buy_config.taker_fee_bps / 10000.0)
        sell_fee = sell_price * quantity * (sell_config.taker_fee_bps / 10000.0)
        pnl = (sell_price - buy_price) * quantity - buy_fee - sell_fee
        self.state.pnl_realized += pnl
        self.metrics.observe("execution_spread_bps", opportunity.spread_bps, {"symbol": opportunity.symbol})
        self.metrics.increment("execution_success_total", {"symbol": opportunity.symbol})
        self.metrics.set_gauge("pnl_realized_usd", self.state.pnl_realized)
        self.journal.record_event(
            "execution",
            {
                "timestamp": time.time(),
                "symbol": opportunity.symbol,
                "buy_order": buy_order,
                "sell_order": sell_order,
                "pnl": pnl,
            },
        )
        return True

    # ------------------------------------------------------------------
    def run_rebalancer(self) -> None:
        exposures: Dict[str, Dict[str, float]] = {}
        for venue in self.config.venue_list:
            connector = self._connectors[venue.name]
            try:
                balances = connector.balances()
            except Exception as exc:  # pragma: no cover - network dependent
                self.metrics.increment("balance_error_total", {"venue": venue.name, "error": str(exc)})
                continue
            exposures[venue.name] = dict(balances)
            for asset, value in balances.items():
                label = {"venue": venue.name, "asset": asset}
                self.metrics.set_gauge("balance", value, label)
        if exposures:
            self.state.balances = exposures
        self._update_unrealized_pnl()

    # ------------------------------------------------------------------
    def _update_unrealized_pnl(self) -> None:
        if not self.state.balances:
            return
        total_value = 0.0
        for venue_name, balances in self.state.balances.items():
            for asset, amount in balances.items():
                total_value += self._asset_value(asset, amount, venue_name)
        if self.state.inventory_baseline == 0.0:
            self.state.inventory_baseline = total_value
        self.state.pnl_unrealized = total_value - self.state.inventory_baseline
        self.metrics.set_gauge("pnl_unrealized_usd", self.state.pnl_unrealized)

    def _asset_value(self, asset: str, amount: float, venue_name: str) -> float:
        if amount == 0:
            return 0.0
        if asset.upper() == "USDT":
            return amount
        symbol = f"{asset}/USDT"
        book = self.state.order_books.get(venue_name, {}).get(symbol)
        if book:
            mid = (book["bid"] + book["ask"]) / 2
            return mid * amount
        # fallback: search other venues
        for books in self.state.order_books.values():
            levels = books.get(symbol)
            if levels:
                mid = (levels["bid"] + levels["ask"]) / 2
                return mid * amount
        return 0.0

    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, object]:
        return {
            "mode": self.config.mode,
            "safe_mode": self.control_state.safe_mode_enabled,
            "hold_reason": self.control_state.hold_reason,
            "pnl": {
                "realized": self.state.pnl_realized,
                "unrealized": self.state.pnl_unrealized,
            },
            "order_books": self.state.order_books,
            "balances": self.state.balances,
        }

    def exposure(self) -> Dict[str, Dict[str, float]]:
        return {name: dict(balances) for name, balances in self.state.balances.items()}

    def connector_names(self) -> List[str]:
        return list(self._connectors.keys())

    def connector(self, name: str) -> Optional[VenueConnector]:
        return self._connectors.get(name)

    def best_opportunity(self) -> Optional[Opportunity]:
        fresh = self._find_opportunities()
        if fresh:
            return max(fresh, key=lambda opp: opp.spread_bps)
        if self.state.opportunities:
            return max(self.state.opportunities, key=lambda opp: opp.spread_bps)
        return None

    def listed_opportunities(self, limit: int = 20) -> List[Opportunity]:
        combined = self._find_opportunities()
        if not combined:
            combined = list(self.state.opportunities)
        combined.sort(key=lambda opp: opp.spread_bps, reverse=True)
        return combined[:limit]

    def execute_opportunity(self, opportunity: Opportunity) -> Dict[str, object]:
        dry_run = self.control_state.safe_mode_enabled
        executed = False
        error: Optional[str] = None
        if not dry_run:
            try:
                executed = self._perform_execution(opportunity)
            except Exception as exc:  # pragma: no cover - network dependent
                error = str(exc)
        status = "dry-run" if dry_run else ("executed" if executed else "rejected")
        record = ExecutionRecord(opportunity=opportunity, executed=executed, reason=error or "")
        self.state.record_execution(record)
        event_payload = {
            "timestamp": time.time(),
            "symbol": opportunity.symbol,
            "buy_venue": opportunity.buy_venue,
            "sell_venue": opportunity.sell_venue,
            "spread_bps": opportunity.spread_bps,
            "status": status,
        }
        if error:
            event_payload["reason"] = error
            self.journal.record_event("manual_execution_error", event_payload)
        else:
            self.journal.record_event("manual_execution", event_payload)
        return {"status": status, "dry_run": dry_run, "executed": executed, "error": error}

    # ------------------------------------------------------------------
    def apply_runtime_config(self, *, min_spread_bps: Optional[float] = None, default_notional_usd: Optional[float] = None) -> None:
        if min_spread_bps is not None:
            self._runtime_min_spread = max(0.0, min_spread_bps)
        if default_notional_usd is not None:
            self._runtime_default_notional = max(0.0, default_notional_usd)

    def runtime_config(self) -> Dict[str, float]:
        return {
            "min_spread_bps": self._runtime_min_spread,
            "default_notional_usd": self._runtime_default_notional,
            "cooldown_seconds": self._cooldown_seconds,
            "safety_margin_bps": self._safety_margin,
        }
