"""FastAPI server for monitoring."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from monitoring.app.config import MonitorConfig
from monitoring.app.state import MonitorState
from monitoring.app.heartbeat_watcher import HeartbeatWatcher

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="Monitoring Service", version="0.1.0")
state = MonitorState()
config = MonitorConfig()
watcher = HeartbeatWatcher(config, state)


class HeartbeatPayload(BaseModel):
    service: str = Field(..., description="Service identifier")
    phase: str | None = Field(None, description="Current phase/state reported by the service")


class EventPayload(BaseModel):
    service: str
    event_type: str
    component: str | None = None
    detail: str | None = None


@app.post("/heartbeat")
def heartbeat(payload: HeartbeatPayload) -> Dict[str, Any]:
    state.register_heartbeat(payload.service, payload.phase)
    state.mark_service_status(payload.service, "up")
    return {"status": "ok"}


@app.post("/events")
def events(payload: EventPayload) -> Dict[str, Any]:
    state.add_event(payload.dict())
    return {"status": "accepted"}


@app.get("/metrics")
def metrics() -> Response:
    state.update_gauges()
    payload = generate_latest(state.registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


@app.get("/events")
def list_events() -> Dict[str, Any]:
    return {"events": state.list_events()}


@app.on_event("startup")
def on_startup() -> None:
    watcher.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    watcher.stop()
