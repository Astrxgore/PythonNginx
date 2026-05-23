"""Access and error logging helpers."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path

from pynginx.config.models import ServerConfig
from pynginx.http.request import HTTPRequest


def setup_file_logger(name: str, path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.FileHandler(path))
    return logger


class AccessLogger:
    def __init__(self, servers: list[ServerConfig]) -> None:
        self._loggers: dict[Path, logging.Logger] = {}
        for server in servers:
            if server.access_log is not None:
                self._loggers[server.access_log] = setup_file_logger(f"access:{server.access_log}", server.access_log)

    def log(
        self,
        server: ServerConfig,
        client_ip: str,
        request: HTTPRequest,
        status: int,
        body_bytes_sent: int,
        elapsed: float,
    ) -> None:
        if server.access_log is None:
            return
        logger = self._loggers.get(server.access_log)
        if logger is None:
            return

        timestamp = datetime.now().astimezone().strftime("%d/%b/%Y:%H:%M:%S %z")
        referer = request.headers.get("referer", "-")
        user_agent = request.headers.get("user-agent", "-")
        request_line = f"{request.method} {request.target} {request.version}".replace('"', r"\"")
        logger.info(
            '%s - - [%s] "%s" %s %s "%s" "%s" %.4f',
            client_ip or "-",
            timestamp,
            request_line,
            status,
            body_bytes_sent,
            referer,
            user_agent,
            elapsed,
        )
