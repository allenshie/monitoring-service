"""Monitoring service config."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _to_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no"}


@dataclass
class MonitorConfig:
    host: str = os.getenv("MONITOR_HOST", "0.0.0.0")
    port: int = int(os.getenv("MONITOR_PORT", "9400"))
    heartbeat_enabled: bool = _to_bool(os.getenv("MONITOR_HEARTBEAT_ENABLED"), True)
    heartbeat_timeout_seconds: int = int(os.getenv("MONITOR_HEARTBEAT_TIMEOUT", "30"))
    heartbeat_check_interval: int = int(os.getenv("MONITOR_HEARTBEAT_CHECK_INTERVAL", "5"))

