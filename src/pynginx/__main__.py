"""Command-line entry point for pynginx."""

from __future__ import annotations

import argparse
import asyncio

from pynginx.config.loader import load_config
from pynginx.server.app import ServerApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PythonNginx server.")
    parser.add_argument("--config", default="config/pynginx.conf", help="Path to config file.")
    return parser.parse_args()


async def amain() -> None:
    args = parse_args()
    config = load_config(args.config)
    app = ServerApp(config)
    await app.serve_forever()


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
