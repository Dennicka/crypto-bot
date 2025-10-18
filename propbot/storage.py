from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

from .config import StorageConfig


class Journal:
    """SQLite-backed durable journal for trading events."""

    def __init__(self, config: StorageConfig) -> None:
        self._path = Path(config.journal_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO journal (ts, type, payload) VALUES (?, ?, ?)",
            (payload.get("timestamp"), event_type, json.dumps(payload)),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
