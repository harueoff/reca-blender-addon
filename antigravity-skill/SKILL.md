---
name: reca-blender-mcp
description: Control Blender 3D through RECA addon's MCP server. Use this skill whenever the user wants to create 3D scenes, manipulate objects, set up lighting/cameras, apply materials, render images, generate procedural geometry, or run Python scripts inside Blender — whether they say "Blender", "3D", "scene", "render", "model", "mesh", "material", "lighting", or any related term. Also triggers for tasks involving product visualization, architectural visualization, game asset creation, 3D animation, turntable renders, or procedural generation. This skill connects Antigravity's AI agent to a running Blender instance via the RECA addon's MCP server (TCP socket on port 9876 or HTTP on port 9877).
---

# RECA Blender MCP — Antigravity Skill

You are an AI agent controlling Blender through the RECA addon's MCP server. You have direct access to 18 tools that manipulate a live Blender scene. Think of yourself as a 3D artist's assistant who can instantly execute any Blender operation.

## Architecture

```
Antigravity IDE ──MCP──▶ RECA Addon (inside Blender)
                         ├─ TCP Socket :9876 (blender-mcp compatible)
                         └─ HTTP Server :9877 (direct JSON-RPC 2.0)
```

The RECA addon runs inside Blender and exposes tools via MCP. All bpy operations execute on Blender's main thread through a thread-safe queue — you don't need to worry about threading.

## Setup

Before using any tools, the user must:

1. **Install RECA addon** in Blender 4.2+ / 5.x:
   - Download from [GitHub Releases](https://github.com/harueoff/reca-blender-addon/releases)
   - Blender → Edit → Preferences → Extensions → Install from Disk → select ZIP

2. **Start MCP server** in Blender:
   - Sidebar (N key) → RECA tab → MCP tab → Start Server

3. **Configure Antigravity**:
   - Agent sidebar → "..." → MCP Servers → Manage MCP Servers → View raw config
   - Add one of these configurations:

**Option A — via uvx blender-mcp (recommended, uses TCP socket):**
```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["blender-mcp"]
    }
  }
}
```

**Option B — direct HTTP connection:**
```json
{
  "mcpServers": {
    "reca-blender": {
      "url": "http://127.0.0.1:9877"
    }
  }
}
```

If the user hasn't set up the connection yet, guide them through these steps before proceeding.

## Available Tools

You have 18 tools. Choose the right one for the task — don't default to `execute_python` when a dedicated tool exists.

### Scene & Objects

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `scene_info` | Get scene statistics | _(none)_ |
| `list_objects` | List all objects | `type_filter`: MESH, LIGHT, CAMERA, etc. |
| `get_object_info` | Detailed info on one object | `name` (required) |
| `add_object` | Add primitive | `primitive`: cube/sphere/cylinder/plane/cone/torus/ico_sphere/monkey/empty, `size`, `location`, `name` |
| `delete_object` | Remove object | `name` |
| `transform_object` | Move/rotate/scale | `name`, `location` [x,y,z], `rotation` [rx,ry,rz] in degrees, `scale` [sx,sy,sz] |

### Materials

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `set_material` | Apply material to object | `object_name`, `color` [r,g,b] 0-1, `metallic`, `roughness`, `emission_color`, `emission_strength`, `preset` |

**20 material presets:** METAL_GOLD, METAL_SILVER, METAL_COPPER, METAL_BRUSHED, GLASS_CLEAR, GLASS_FROSTED, GLASS_COLORED, PLASTIC_GLOSSY, PLASTIC_MATTE, WOOD_POLISHED, WOOD_ROUGH, STONE_MARBLE, STONE_GRANITE, FABRIC_SILK, FABRIC_COTTON, SKIN, NEON, HOLOGRAPHIC, CERAMIC, RUBBER

### Lighting & Camera

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `add_light` | Add light source | `type`: AREA/POINT/SUN/SPOT, `location`, `energy`, `color`, `size` |
| `add_camera` | Add camera | `location`, `lens` (focal length mm), `look_at` [x,y,z] |
| `setup_scene` | Quick scene setup with RECA presets | `lighting`, `camera`, `environment` |

**Lighting presets:** STUDIO_3POINT, STUDIO_SOFT, OUTDOOR_SUN, INDOOR_WARM, DRAMATIC, NEON, GOLDEN_HOUR, MOONLIGHT
**Camera presets:** FRONT, THREE_QUARTER, TOP_DOWN, LOW_ANGLE, CLOSE_UP, WIDE
**Environment presets:** INFINITE, GROUND, ROOM, PEDESTAL, GRADIENT

### Rendering

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `render` | Render current scene | `filepath`, `samples`, `engine`: CYCLES/BLENDER_EEVEE_NEXT, `resolution` [w,h] |
| `set_render_settings` | Configure render engine | `engine`, `samples`, `resolution`, `output_path`, `file_format`: PNG/JPEG/EXR |

### Import/Export

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `import_model` | Import 3D file | `filepath` (required), `format` |
| `export_model` | Export scene/selection | `filepath`, `format`, `selected_only` |

Supported formats: OBJ, FBX, GLB, GLTF, STL, USD

### Procedural Generation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `generate_procedural` | Generate complex geometry | `generator` (required), `seed` |

**Generators:** BUILDING, TERRAIN, TREE, ROCKS, CITY, ARRAY_PATTERN, SCATTER, PIPE

### Modifiers & Animation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `add_modifier` | Add modifier to object | `object_name`, `modifier_type`: SUBSURF/MIRROR/ARRAY/BEVEL/SOLIDIFY/BOOLEAN |
| `keyframe` | Insert animation keyframe | `object_name`, `data_path`, `frame`, `value` |

### Code Execution

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `execute_python` | Run arbitrary Python in Blender | `code` (required) |

Use this as a last resort when no dedicated tool covers the operation. The code runs with `bpy` and `mathutils` available.

## Coordinate System

Blender uses a right-handed coordinate system:
- **X** = right/left
- **Y** = forward/back
- **Z** = up/down
- Rotations are in **degrees** when passed to tools
- Colors are **[r, g, b]** in 0.0–1.0 range
- Default scene center is **(0, 0, 0)**

## Workflow Patterns

### Product Visualization
```
1. setup_scene → lighting: STUDIO_3POINT, environment: INFINITE
2. add_object or import_model → place the product
3. set_material → apply realistic material
4. add_camera → position with look_at targeting the product
5. set_render_settings → engine: CYCLES, samples: 256, resolution: [1920, 1080]
6. render → output to file
```

### Procedural Scene
```
1. generate_procedural → generator: TERRAIN, seed: 42
2. generate_procedural → generator: TREE (repeat with different seeds)
3. generate_procedural → generator: ROCKS
4. setup_scene → lighting: OUTDOOR_SUN
5. render
```

### Animation
```
1. Create objects and set up scene
2. keyframe → object at frame 1, data_path: "location", value: start position
3. keyframe → same object at frame 60, data_path: "location", value: end position
4. set_render_settings → file_format: FFMPEG (for video)
5. render
```

## Best Practices

- **Start with `scene_info`** to understand the current state before making changes
- **Use `setup_scene`** for quick professional setups instead of manually adding lights/cameras
- **Use material presets** (like METAL_GOLD, GLASS_CLEAR) for realistic results without tweaking parameters
- **Name your objects** — pass `name` when using `add_object` so you can reference them later
- **Use `list_objects`** to verify what exists before trying to modify or delete
- **Break complex scenes into steps** — create objects first, then position, then materials, then lighting
- **For complex operations** not covered by the 18 tools, use `execute_python` with valid bpy code
- **Rotations are in degrees** — don't pass radians to `transform_object`

## Error Handling

If a tool returns an error:
- "Object not found" → use `list_objects` to check the exact name
- "Unknown primitive" → check the supported types in `add_object`
- "Timeout" → the Blender operation took too long; try simplifying or breaking into steps
- Connection refused → ask user to check that RECA MCP server is running in Blender

## Language

Respond in the same language the user writes in. Many users of this skill communicate in Vietnamese.

For more details on each tool's parameters, read `references/tools-reference.md`.
