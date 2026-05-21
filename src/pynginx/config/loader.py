"""Load pynginx config files.

The first implementation should use configparser and fill models.py dataclasses.
"""

from __future__ import annotations

import configparser
from pathlib import Path

from pynginx.config.models import AppConfig, LocationConfig, ServerConfig


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "yes", "true", "on"}


def _parse_listen(value: str) -> tuple[str, int]:
    host, port = value.rsplit(":", 1)
    return host, int(port)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    parser = configparser.ConfigParser()
    read_files = parser.read(config_path)
    if not read_files:
        raise FileNotFoundError(config_path)

    servers: dict[str, ServerConfig] = {}
    locations: list[tuple[str, LocationConfig]] = []

    for section in parser.sections():
        data = parser[section]
        if section.startswith("server:"):
            name = section.split(":", 1)[1]
            listen_host, listen_port = _parse_listen(data.get("listen", "127.0.0.1:8080"))
            servers[name] = ServerConfig(
                name=name,
                listen_host=listen_host,
                listen_port=listen_port,
                server_names=data.get("server_name", name).split(),
                root=Path(data.get("root", "public")),
                autoindex=_as_bool(data.get("autoindex")),
                access_log=Path(data["access_log"]) if data.get("access_log") else None,
            )
        elif section.startswith("location:"):
            _, server_name, prefix = section.split(":", 2)
            locations.append(
                (
                    server_name,
                    LocationConfig(
                        prefix=prefix,
                        root=Path(data["root"]) if data.get("root") else None,
                        autoindex=_as_bool(data.get("autoindex")) if data.get("autoindex") else None,
                        proxy_pass=data.get("proxy_pass"),
                    ),
                )
            )

    for server_name, location in locations:
        if server_name not in servers:
            raise ValueError(f"location references unknown server: {server_name}")
        servers[server_name].locations.append(location)

    if not servers:
        raise ValueError("config must contain at least one [server:name] section")

    return AppConfig(servers=list(servers.values()))
