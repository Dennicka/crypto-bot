from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Callable, Dict

from ..engine.metrics import MetricsRegistry
from ..engine.state import ControlState


@dataclass
class ScheduledTask:
    name: str
    callback: Callable[[], None]
    interval_seconds: float
    last_run: float = 0.0


class Scheduler:
    """A cooperative scheduler that runs engine tasks."""

    def __init__(self, *, metrics: MetricsRegistry, control_state: ControlState) -> None:
        self._metrics = metrics
        self._control_state = control_state
        self._tasks: Dict[str, ScheduledTask] = {}
        self._lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None

    def register_task(self, name: str, callback: Callable[[], None], *, interval_seconds: float) -> None:
        with self._lock:
            self._tasks[name] = ScheduledTask(name=name, callback=callback, interval_seconds=interval_seconds)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            now = time.monotonic()
            with self._lock:
                tasks = list(self._tasks.values())
            for task in tasks:
                if now - task.last_run < task.interval_seconds:
                    continue
                if self._control_state.is_hold:
                    continue
                start = time.perf_counter()
                try:
                    task.callback()
                except Exception:  # pragma: no cover - metrics handles logging via observers
                    self._metrics.increment("task_errors", {"task": task.name})
                finally:
                    elapsed = time.perf_counter() - start
                    task.last_run = now
                    self._metrics.observe("task_duration_seconds", elapsed, {"task": task.name})
            time.sleep(0.1)
