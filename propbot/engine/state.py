from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional


@dataclass
class Opportunity:
    symbol: str
    buy_venue: str
    sell_venue: str
    spread_bps: float
    notional: float
    timestamp: float


@dataclass
class ExecutionRecord:
    opportunity: Opportunity
    executed: bool
    reason: str = ""


@dataclass
class EngineState:
    order_books: Dict[str, Dict[str, float]] = field(default_factory=dict)
    balances: Dict[str, float] = field(default_factory=dict)
    opportunities: List[Opportunity] = field(default_factory=list)
    executions: List[ExecutionRecord] = field(default_factory=list)
    pnl_realized: float = 0.0
    pnl_unrealized: float = 0.0

    @classmethod
    def make_default(cls) -> "EngineState":
        return cls()

    def record_opportunity(self, opportunity: Opportunity) -> None:
        self.opportunities.append(opportunity)
        if len(self.opportunities) > 100:
            self.opportunities = self.opportunities[-100:]

    def record_execution(self, execution: ExecutionRecord) -> None:
        self.executions.append(execution)
        if len(self.executions) > 100:
            self.executions = self.executions[-100:]


@dataclass
class ControlState:
    safe_mode_enabled: bool = True
    hold_reason: Optional[str] = None
    confirmations_required: int = 2
    confirmations_received: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def hold(self, reason: str) -> None:
        with self._lock:
            self.hold_reason = reason
            self.confirmations_received = 0

    def resume(self) -> None:
        with self._lock:
            self.hold_reason = None
            self.confirmations_received = 0

    def request_resume(self) -> bool:
        with self._lock:
            if not self.safe_mode_enabled:
                self.resume()
                return True
            self.confirmations_received += 1
            if self.confirmations_received >= self.confirmations_required:
                self.resume()
                return True
        return False

    @property
    def is_hold(self) -> bool:
        return self.hold_reason is not None

    def toggle_safe_mode(self, enabled: bool) -> None:
        with self._lock:
            self.safe_mode_enabled = enabled
            if enabled:
                if not self.is_hold:
                    self.hold_reason = "SAFE_MODE_ENABLED"
            else:
                self.hold_reason = None
                self.confirmations_received = 0
