from __future__ import annotations

import time
from typing import Dict, List, Optional

from ..config import AppConfig, VenueConfig
from ..connectors.binance import BinanceConnector
from ..connectors.okx import OKXConnector
from ..engine.metrics import MetricsRegistry
from ..engine.state import ControlState, EngineState, ExecutionRecord, Opportunity
from ..storage import Journal
from ..connectors.base import VenueConnector

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
        self._connectors: Dict[str, VenueConnector] = {}
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
        return self._perform_execution(opportunity)

    def _perform_execution(self, opportunity: Opportunity) -> bool:
        buy_connector = self._connectors[opportunity.buy_venue]
        sell_connector = self._connectors[opportunity.sell_venue]
        qty = opportunity.notional / max(self.state.order_books[opportunity.buy_venue]["ask"], 1e-6)
        try:
            buy_order = buy_connector.place_order(opportunity.symbol, "buy", qty)
            sell_order = sell_connector.place_order(opportunity.symbol, "sell", qty)
        except ValueError as exc:  # insufficient balance
            self.metrics.increment("execution_rejected_total", {"reason": str(exc)})
            raise
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
            except ValueError as exc:
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
        return {
            "status": status,
            "dry_run": dry_run,
            "executed": executed,
            "error": error,
        }
