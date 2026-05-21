"""Directory autoindex rendering."""

from __future__ import annotations

import html
from pathlib import Path


def render_autoindex(request_path: str, directory: Path) -> str:
    rows = []
    if request_path != "/":
        rows.append('<li><a href="../">../</a></li>')
    for child in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        name = child.name + ("/" if child.is_dir() else "")
        escaped = html.escape(name)
        rows.append(f'<li><a href="{escaped}">{escaped}</a></li>')
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>Index of {html.escape(request_path)}</title></head>"
        f"<body><h1>Index of {html.escape(request_path)}</h1><ul>"
        + "".join(rows)
        + "</ul></body></html>"
    )
