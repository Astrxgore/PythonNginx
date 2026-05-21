"""Access and error logging helpers."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_file_logger(name: str, path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.FileHandler(path))
    return logger
