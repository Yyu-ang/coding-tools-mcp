"""Frozen desktop-to-server executable discovery.

Keep packaging-specific path logic out of the upstream RuntimeManager.
"""
from __future__ import annotations

import sys
from pathlib import Path


SERVER_EXE_NAME = "coding-tools-mcp-server.exe"


def frozen_server_command(
    *, executable: str | Path | None = None, frozen: bool | None = None
) -> list[str] | None:
    """Return the installed MCP server command, or None for source installs.

    An incomplete frozen installation is a hard error: falling back to PATH
    could accidentally run an older or differently configured MCP server.
    """
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if not frozen:
        return None

    desktop_executable = Path(executable if executable is not None else sys.executable).resolve()
    server = desktop_executable.parent / "server" / SERVER_EXE_NAME
    if not server.is_file():
        raise FileNotFoundError(
            f"Bundled MCP server is missing: {server}. "
            "Repair or reinstall Coding Tools MCP Desktop."
        )
    return [str(server)]
