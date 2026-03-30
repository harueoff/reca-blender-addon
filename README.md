# RECA - All-in-One 3D Toolkit for Blender 5.1.0

A professional-grade, multi-purpose Blender addon with 8 integrated modules.

## Features

| Module | Description |
|--------|-------------|
| **Scene Builder** | 8 lighting presets, 6 camera presets, 5 environment types, quick scene setup |
| **Batch Processor** | 7 batch operations, file scanning, format conversion (OBJ/FBX/GLB/STL/USD) |
| **Procedural Generator** | 8 generators: Building, Terrain, Tree, Rocks, City, Array, Scatter, Pipe |
| **Quick Tools** | Align, Distribute, Mirror, Random Transform, Smart Select, Copy Attributes |
| **Render Manager** | 9 render presets, turntable animation, render all cameras, clay override |
| **Material Tools** | 20 PBR presets, custom material builder, random materials, bake to vertex |
| **MCP Server** | 16 AI-controllable tools via JSON-RPC 2.0, HTTP server for AI agents |
| **AI Integration** | 6 AI providers: OpenClaw, Google Antigravity, Anthropic, OpenAI, Ollama, Custom |

## Installation

1. Download the latest release ZIP
2. In Blender: `Edit > Preferences > Add-ons > Install from Disk`
3. Select the ZIP file and enable "RECA - All-in-One 3D Toolkit"

## MCP Server

The built-in MCP server allows AI agents (Claude Code, OpenClaw.ai, Cursor, etc.) to control Blender remotely.

**Default endpoint:** `http://127.0.0.1:9876`

### MCP Config (for Claude Code / OpenClaw / Cursor)

```json
{
  "mcpServers": {
    "blender-reca": {
      "url": "http://127.0.0.1:9876"
    }
  }
}
```

### Available MCP Tools

`scene_info` `list_objects` `add_object` `delete_object` `transform_object` `set_material` `render` `import_model` `export_model` `execute_python` `setup_scene` `generate_procedural` `add_modifier` `add_light` `add_camera` `keyframe`

## Requirements

- Blender 5.1.0+
- No external Python dependencies (uses only stdlib + bpy)

## License

GPL-3.0-or-later
