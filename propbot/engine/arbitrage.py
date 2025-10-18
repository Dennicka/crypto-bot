from __future__ import annotations

import time
from typing import Dict, List

from ..config import AppConfig, VenueConfig
from ..connectors.binance import BinanceConnector
from ..connectors.okx import OKXConnector
from ..engine.metrics import MetricsRegistry
from ..engine.state import ControlState, EngineState, ExecutionRecord, Opportunity
from ..storage import Journal

CONNECTOR_FACTORIES = {
    "binance": BinanceConnector,
    "okx": OKXConnector,
}


class ArbitrageEngine:
    """Evaluate opportunities between two venues and simulate execution."""

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
        self._connectors: Dict[str, object] = {}
        for venue in config.venue_list:
            factory = CONNECTOR_FACTORIES.get(venue.name.lower())
            if factory is None:
                factory = CONNECTOR_FACTORIES["binance"]
            self._connectors[venue.name] = factory(venue)
        if config.safe_mode.hold_on_startup:
            self.control_state.hold("SAFE_MODE_STARTUP")

    def poll_market_data(self) -> None:
        for venue in self.config.venue_list:
            connector = self._connectors[venue.name]
            book = connector.refresh_order_book()
            self.state.order_books[venue.name] = book
            self.metrics.observe(
                "ws_gap_ms_p95",
                amount=book["ask"] - book["bid"],
                labels={"venue": venue.name},
            )

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
            payload = {
                "timestamp": opp.timestamp,
                "symbol": opp.symbol,
                "buy_venue": opp.buy_venue,
                "sell_venue": opp.sell_venue,
                "spread_bps": opp.spread_bps,
                "notional": opp.notional,
                "executed": executed,
            }
            self.journal.record_event("opportunity", payload)

    def _find_opportunities(self) -> List[Opportunity]:
        if len(self.state.order_books) < 2:
            return []
        timestamp = time.time()
        opportunities: List[Opportunity] = []
        venue_names = list(self.state.order_books.keys())
        symbols = self.config.venue_list[0].trading_pairs
        for i, buy_venue in enumerate(venue_names):
            for sell_venue in venue_names[i + 1 :]:
                buy_book = self.state.order_books[buy_venue]
                sell_book = self.state.order_books[sell_venue]
                for symbol in symbols:
                    spread = (sell_book["bid"] - buy_book["ask"]) / max(buy_book["ask"], 1e-6) * 10000
                    if spread > 5:
                        opportunities.append(
                            Opportunity(
                                symbol=symbol,
                                buy_venue=buy_venue,
                                sell_venue=sell_venue,
                                spread_bps=spread,
                                notional=self.config.risk.max_single_order_usd,
                                timestamp=timestamp,
                            )
                        )
                    reverse_spread = (buy_book["bid"] - sell_book["ask"]) / max(sell_book["ask"], 1e-6) * 10000
                    if reverse_spread > 5:
                        opportunities.append(
                            Opportunity(
                                symbol=symbol,
                                buy_venue=sell_venue,
                                sell_venue=buy_venue,
                                spread_bps=reverse_spread,
                                notional=self.config.risk.max_single_order_usd,
                                timestamp=timestamp,
                            )
                        )
        return opportunities

    def _execute_if_allowed(self, opportunity: Opportunity) -> bool:
        if self.control_state.safe_mode_enabled:
            return False
        buy_connector = self._connectors[opportunity.buy_venue]
        sell_connector = self._connectors[opportunity.sell_venue]
        qty = opportunity.notional / self.state.order_books[opportunity.buy_venue]["ask"]
        try:
            buy_order = buy_connector.place_order(opportunity.symbol, "buy", qty)
            sell_order = sell_connector.place_order(opportunity.symbol, "sell", qty)
        except ValueError as exc:  # insufficient balance
            self.metrics.increment("execution_rejected_total", {"reason": str(exc)})
            return False
        pnl = sell_order["price"] - buy_order["price"]
        self.state.pnl_realized += pnl * qty
        self.metrics.observe("order_cycle_ms_p95", 120, {"path": "simulated"})
        self.metrics.set_gauge("pnl_realized_usd", self.state.pnl_realized)
        return True

    def run_rebalancer(self) -> None:
        for venue in self.config.venue_list:
            connector = self._connectors[venue.name]
            balances = connector.balances()
            for asset, value in balances.items():
                label = {"venue": venue.name, "asset": asset}
                self.metrics.set_gauge("balance", value, label)

    def snapshot(self) -> Dict[str, object]:
        return {
            "mode": self.config.mode,
            "safe_mode": self.control_state.safe_mode_enabled,
            "hold_reason": self.control_state.hold_reason,
            "pnl": {
                "realized": self.state.pnl_realized,
                "unrealized": self.state.pnl_unrealized,
            },
            "balances": self.state.order_books,
        }

    def exposure(self) -> Dict[str, Dict[str, float]]:
        exposures: Dict[str, Dict[str, float]] = {}
        for venue in self.config.venue_list:
            connector = self._connectors[venue.name]
            exposures[venue.name] = connector.balances()
        return exposures

    def connector_names(self) -> List[str]:
        return list(self._connectors.keys())
