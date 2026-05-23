"""Dataclass models for parsed configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class LocationConfig:
    prefix: str
    root: Path | None = None
    autoindex: bool | None = None
    proxy_pass: str | None = None


@dataclass(slots=True)
class ServerConfig:
    name: str
    listen_host: str
    listen_port: int
    server_names: list[str]
    root: Path
    autoindex: bool = False
    access_log: Path | None = None
    locations: list[LocationConfig] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    servers: list[ServerConfig]
    header_limit: int = 16 * 1024
    body_limit: int = 2 * 1024 * 1024
    keepalive_timeout: float = 30.0
    keepalive_max_requests: int = 100
    open_file_cache_max: int = 128
    open_file_cache_inactive: float = 30.0
    proxy_timeout: float = 10.0
