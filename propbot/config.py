from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import dotenv_values


class VenueCredentials(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""


class VenueConfig(BaseModel):
    name: str
    type: str = Field(default="spot")
    trading_pairs: List[str]
    fees_bps: float = 7.5
    taker_fee_bps: float = 7.5
    maker_fee_bps: float = 1.0
    min_notional: float = 10.0
    credentials: VenueCredentials = Field(default_factory=VenueCredentials)
    weight: float = 0.5
    simulate: bool = True


class StorageConfig(BaseModel):
    journal_path: Path = Path("data/journal.sqlite3")
    archive_path: Path = Path("data/archive")


class RiskLimits(BaseModel):
    max_position_usd: float = 1000.0
    max_single_order_usd: float = 200.0
    max_daily_drawdown_usd: float = 200.0
    stop_loss_bps: float = 30.0
    hold_on_drawdown: bool = True


class SafeModeConfig(BaseModel):
    enabled: bool = True
    hold_on_startup: bool = True
    require_double_confirmation: bool = True


class SchedulerConfig(BaseModel):
    max_workers: int = 4
    tick_interval_ms: int = 250


class AppConfig(BaseModel):
    mode: str = Field(pattern=r"^(paper|testnet|live)$")
    safe_mode: SafeModeConfig = Field(default_factory=SafeModeConfig)
    venues: Dict[str, VenueConfig]
    risk: RiskLimits = Field(default_factory=RiskLimits)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    ui_base_url: str = "http://localhost:8000"

    @property
    def venue_list(self) -> List[VenueConfig]:
        return list(self.venues.values())


def _load_env_file(env_file: Optional[Path]) -> Dict[str, str]:
    if env_file and env_file.exists():
        return {k: str(v) for k, v in dotenv_values(env_file).items() if k}
    return {}


def _expand_env(data: str, env: Dict[str, str]) -> str:
    os_env = {**env, **os.environ}
    for key, value in os_env.items():
        if value is None:
            continue
        data = data.replace(f"${{{key}}}", value)
    return data


def load_config(path: Path, *, env_file: Optional[Path] = None) -> AppConfig:
    raw = path.read_text(encoding="utf-8")
    env_values = _load_env_file(env_file)
    expanded = _expand_env(raw, env_values)
    content = yaml.safe_load(expanded)
    if not isinstance(content, dict):
        raise ValueError("Configuration file is malformed")
    return AppConfig.model_validate(content)
