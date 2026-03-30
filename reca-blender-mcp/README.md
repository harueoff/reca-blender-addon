# reca-blender-mcp

MCP server for controlling Blender via the [RECA addon](https://github.com/harueoff/reca-blender-addon). Enables AI agents (Claude Desktop, Antigravity, Cursor, Claude Code) to manipulate 3D scenes, objects, materials, lighting, rendering, and more — all through natural language.

## 18 Tools

| Category | Tools |
|----------|-------|
| Scene | `blender_get_scene_info`, `blender_list_objects`, `blender_get_object_info` |
| Objects | `blender_add_object`, `blender_delete_object`, `blender_transform_object` |
| Materials | `blender_set_material` (20 PBR presets) |
| Lighting | `blender_add_light`, `blender_add_camera`, `blender_setup_scene` |
| Rendering | `blender_render`, `blender_set_render_settings` |
| Import/Export | `blender_import_model`, `blender_export_model` |
| Procedural | `blender_generate_procedural` (8 generators) |
| Animation | `blender_add_modifier`, `blender_keyframe` |
| Advanced | `blender_execute_python` |

## Setup

### 1. Install RECA addon in Blender

Download from [Releases](https://github.com/harueoff/reca-blender-addon/releases), then:
- Blender → Edit → Preferences → Extensions → Install from Disk → select ZIP

### 2. Start MCP server in Blender

- Press `N` to open sidebar → RECA tab → MCP → **Start Server**

### 3. Configure your AI client

#### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["reca-blender-mcp"]
    }
  }
}
```

#### Google Antigravity

Agent sidebar → "..." → MCP Servers → Manage → View raw config:

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["reca-blender-mcp"]
    }
  }
}
```

#### Cursor

Settings → MCP → Add Server:

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["reca-blender-mcp"]
    }
  }
}
```

#### Claude Code

```bash
claude mcp add blender uvx reca-blender-mcp
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BLENDER_HOST` | `localhost` | Blender socket server host |
| `BLENDER_PORT` | `9876` | Blender socket server port |

## Examples

Ask your AI assistant:
- "Create a product scene with a metallic sphere on a pedestal"
- "Generate a low-poly city with dramatic lighting"
- "Render the scene at 4K with Cycles"
- "Import model.fbx and apply gold material"
- "Animate the cube moving from left to right over 60 frames"

## License

MIT
