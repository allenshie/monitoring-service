"""Stores heartbeat info and events."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, List

from prometheus_client import CollectorRegistry, Counter, Gauge


@dataclass
class HeartbeatRecord:
    service: str
    phase: str
    last_seen: datetime
    status: str = "up"


class MonitorState:
    def __init__(self, max_events: int = 500) -> None:
        self._events: Deque[Dict[str, str]] = deque(maxlen=max_events)
        self._heartbeats: Dict[str, HeartbeatRecord] = {}
        self._lock = threading.Lock()
        self.registry = CollectorRegistry()
        self.service_status = Gauge(
            "monitoring_service_status",
            "1 if service heartbeat is healthy, 0 otherwise",
            ["service", "phase"],
            registry=self.registry,
        )
        self.service_last_seen = Gauge(
            "monitoring_service_last_seen_seconds",
            "Seconds since last heartbeat",
            ["service", "phase"],
            registry=self.registry,
        )
        self.event_counter = Counter(
            "monitoring_events_total",
            "Total events reported by services",
            ["service", "event_type"],
            registry=self.registry,
        )
        self.task_failures = Counter(
            "monitoring_task_failures_total",
            "Total workflow task failures per service",
            ["service", "task"],
            registry=self.registry,
        )
        self.task_success = Counter(
            "monitoring_task_success_total",
            "Total workflow task success per service",
            ["service", "task"],
            registry=self.registry,
        )

    def register_heartbeat(self, service: str, phase: str | None = None) -> None:
        with self._lock:
            now = datetime.now(timezone.utc)
            phase_label = phase or "unknown"
            record = self._heartbeats.get(service)
            if record is None:
                record = HeartbeatRecord(service=service, phase=phase_label, last_seen=now)
            else:
                record.last_seen = now
                record.phase = phase_label
            record.status = "up"
            self._heartbeats[service] = record
            self.service_status.labels(service=service, phase=phase_label).set(1)
            self.service_last_seen.labels(service=service, phase=phase_label).set(0)

    def update_gauges(self) -> None:
        with self._lock:
            now = datetime.now(timezone.utc)
            for record in self._heartbeats.values():
                age = (now - record.last_seen).total_seconds()
                self.service_last_seen.labels(service=record.service, phase=record.phase).set(age)

    def mark_service_status(self, service: str, status: str) -> None:
        with self._lock:
            record = self._heartbeats.get(service)
            if record is None:
                record = HeartbeatRecord(service=service, phase="unknown", last_seen=datetime.now(timezone.utc))
            record.status = status
            self._heartbeats[service] = record
            value = 1 if status == "up" else 0
            self.service_status.labels(service=record.service, phase=record.phase).set(value)

    def add_event(self, event: Dict[str, str]) -> None:
        with self._lock:
            event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            self._events.append(event)
            service = event.get("service", "unknown")
            event_type = event.get("event_type", "unknown")
            component = event.get("component")
            self.event_counter.labels(service=service, event_type=event_type).inc()
            if component:
                if event_type == "failure":
                    self.task_failures.labels(service=service, task=component).inc()
                elif event_type == "success":
                    self.task_success.labels(service=service, task=component).inc()

    def list_events(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._events)

    def list_heartbeats(self) -> List[HeartbeatRecord]:
        with self._lock:
            return list(self._heartbeats.values())
