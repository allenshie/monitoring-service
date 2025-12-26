"""Entry point for monitoring service."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import uvicorn

if __package__ in {None, ""}:  # executed as "python main.py"
    current_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(current_dir))
    from app.server import app, config as server_config  # type: ignore
else:  # executed as module (python -m monitoring.main)
    from .app.server import app, config as server_config

LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cfg = server_config
    uvicorn.run(app, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
