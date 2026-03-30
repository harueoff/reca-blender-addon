"""RECA Blender MCP Server — Control Blender via RECA addon's TCP socket.

Architecture:
  AI Client (Claude/Antigravity/Cursor)
    → stdio → reca-blender-mcp (this server)
      → TCP socket → RECA addon (inside Blender, port 9876)

Usage:
  uvx reca-blender-mcp
  # or
  pip install reca-blender-mcp && reca-blender-mcp
"""

from .server import main

__all__ = ["main"]
