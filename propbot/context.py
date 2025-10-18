from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import AppConfig, load_config
from .engine.arbitrage import ArbitrageEngine
from .engine.metrics import MetricsRegistry
from .engine.state import ControlState, EngineState
from .services.scheduler import Scheduler
from .storage import Journal


@dataclass
class AppContext:
    """Holds the wiring for the arbitrage application."""

    config_path: Path
    env_file: Optional[Path]
    config: AppConfig
    metrics: MetricsRegistry
    journal: Journal
    engine_state: EngineState
    control_state: ControlState
    scheduler: Scheduler
    engine: ArbitrageEngine

    @classmethod
    def from_file(cls, path: Path, *, env_file: Optional[Path] = None) -> "AppContext":
        config = load_config(path, env_file=env_file)
        metrics = MetricsRegistry()
        journal = Journal(config.storage)
        engine_state = EngineState.make_default()
        control_state = ControlState()
        scheduler = Scheduler(metrics=metrics, control_state=control_state)
        engine = ArbitrageEngine(
            config=config,
            metrics=metrics,
            journal=journal,
            state=engine_state,
            control_state=control_state,
        )
        scheduler.register_task("poll_order_books", engine.poll_market_data, interval_seconds=1.0)
        scheduler.register_task("evaluate_opportunities", engine.evaluate, interval_seconds=1.0)
        scheduler.register_task("rebalance", engine.run_rebalancer, interval_seconds=60.0)
        return cls(
            config_path=path,
            env_file=env_file,
            config=config,
            metrics=metrics,
            journal=journal,
            engine_state=engine_state,
            control_state=control_state,
            scheduler=scheduler,
            engine=engine,
        )

    def start(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.stop()
        self.journal.close()

    def apply_engine_overrides(self, *, min_spread_bps: Optional[float] = None, default_notional_usd: Optional[float] = None) -> None:
        self.engine.apply_runtime_config(
            min_spread_bps=min_spread_bps,
            default_notional_usd=default_notional_usd,
        )
        if min_spread_bps is not None:
            self.config.engine.min_spread_bps = min_spread_bps
        if default_notional_usd is not None:
            self.config.engine.default_notional_usd = default_notional_usd
