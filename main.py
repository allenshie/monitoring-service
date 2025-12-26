"""Entry point for monitoring service."""
from __future__ import annotations

import logging
import os
import sys

import uvicorn

if __name__ == "__main__":  # script execution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    from monitoring.app.server import app, config as server_config
else:
    from .app.server import app, config as server_config

LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cfg = server_config
    uvicorn.run(app, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
