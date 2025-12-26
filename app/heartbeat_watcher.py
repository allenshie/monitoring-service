"""Background thread to mark services down when heartbeats expire."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from .config import MonitorConfig
from .state import MonitorState

LOGGER = logging.getLogger(__name__)


class HeartbeatWatcher:
    """Manages the background watcher lifecycle for graceful shutdown."""

    def __init__(self, config: MonitorConfig, state: MonitorState) -> None:
        self._config = config
        self._state = state
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if not self._config.heartbeat_enabled:
            LOGGER.info("heartbeat watcher disabled")
            return
        if self._thread and self._thread.is_alive():
            LOGGER.debug("heartbeat watcher already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="heartbeat-watcher", daemon=False)
        self._thread.start()

    def stop(self) -> None:
        if not self._thread:
            return
        LOGGER.info("stopping heartbeat watcher")
        self._stop_event.set()
        self._thread.join(timeout=self._config.heartbeat_check_interval + 5)
        self._thread = None

    def _loop(self) -> None:
        LOGGER.info("heartbeat watcher started")
        check_interval = max(1, self._config.heartbeat_check_interval)
        while not self._stop_event.is_set():
            heartbeats = self._state.list_heartbeats()
            now = datetime.now(timezone.utc)
            for rec in heartbeats:
                age = (now - rec.last_seen).total_seconds()
                if age > self._config.heartbeat_timeout_seconds and rec.status != "down":
                    LOGGER.warning("service %s heartbeat timeout (age=%s)", rec.service, age)
                    self._state.mark_service_status(rec.service, "down")
            self._stop_event.wait(check_interval)
        LOGGER.info("heartbeat watcher stopped")
