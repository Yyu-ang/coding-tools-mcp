"""PyInstaller console entry point for the standalone MCP server.

Keep the server's real CLI implementation in coding_tools_mcp.server.
"""
from coding_tools_mcp.server import main


if __name__ == "__main__":
    raise SystemExit(main())
