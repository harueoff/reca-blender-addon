# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA MCP Server — Model Context Protocol server for AI agent control.

Exposes Blender operations as MCP tools so AI agents (OpenClaw, Claude Code,
Codex, Cursor, etc.) can control Blender programmatically via JSON-RPC 2.0
over HTTP or stdio.

Architecture:
  - Runs a lightweight HTTP server in a background thread
  - All Blender operations are queued and executed on the main thread
    via bpy.app.timers (Blender doesn't allow bpy calls from threads)
  - Tools are auto-registered from the TOOLS dict
"""

import bpy
import json
import os
import threading
import queue
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    BoolProperty,
    IntProperty,
    StringProperty,
    PointerProperty,
    EnumProperty,
)


# ─────────────────────────────────────────────
#  Execution Queue (thread-safe → main thread)
# ─────────────────────────────────────────────

_request_queue = queue.Queue()
_response_map = {}
_response_events = {}
_request_counter = 0
_counter_lock = threading.Lock()


def _next_id():
    global _request_counter
    with _counter_lock:
        _request_counter += 1
        return _request_counter


def _queue_blender_call(func, args=None):
    """Queue a function to run on the main thread and wait for result."""
    rid = _next_id()
    event = threading.Event()
    _response_events[rid] = event
    _request_queue.put((rid, func, args or {}))
    event.wait(timeout=30)
    result = _response_map.pop(rid, {"error": "Timeout"})
    _response_events.pop(rid, None)
    return result


def _process_queue():
    """Timer callback — runs on main thread, processes queued requests."""
    while not _request_queue.empty():
        try:
            rid, func, args = _request_queue.get_nowait()
            try:
                result = func(**args)
                _response_map[rid] = {"result": result}
            except Exception as e:
                _response_map[rid] = {"error": str(e), "traceback": traceback.format_exc()}
            finally:
                event = _response_events.get(rid)
                if event:
                    event.set()
        except queue.Empty:
            break
    return 0.1  # Run every 100ms


# ─────────────────────────────────────────────
#  MCP Tool Definitions
# ─────────────────────────────────────────────

def _tool_scene_info():
    """Get current scene statistics."""
    from ..utils import scene_stats
    return scene_stats()


def _tool_list_objects(type_filter=None):
    """List all objects in scene, optionally filtered by type."""
    result = []
    for obj in bpy.data.objects:
        if type_filter and obj.type != type_filter.upper():
            continue
        info = {
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "visible": obj.visible_get(),
        }
        if obj.type == 'MESH' and obj.data:
            info["vertices"] = len(obj.data.vertices)
            info["faces"] = len(obj.data.polygons)
        result.append(info)
    return result


def _tool_add_object(primitive="cube", size=1.0, location=None, name=None):
    """Add a primitive object to the scene."""
    loc = tuple(location) if location else (0, 0, 0)
    primitives = {
        "cube": lambda: bpy.ops.mesh.primitive_cube_add(size=size, location=loc),
        "sphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=size/2, location=loc),
        "cylinder": lambda: bpy.ops.mesh.primitive_cylinder_add(radius=size/2, depth=size, location=loc),
        "plane": lambda: bpy.ops.mesh.primitive_plane_add(size=size, location=loc),
        "cone": lambda: bpy.ops.mesh.primitive_cone_add(radius1=size/2, depth=size, location=loc),
        "torus": lambda: bpy.ops.mesh.primitive_torus_add(major_radius=size, minor_radius=size*0.3, location=loc),
        "ico_sphere": lambda: bpy.ops.mesh.primitive_ico_sphere_add(radius=size/2, location=loc),
        "monkey": lambda: bpy.ops.mesh.primitive_monkey_add(size=size, location=loc),
    }
    fn = primitives.get(primitive.lower())
    if fn is None:
        return {"error": f"Unknown primitive: {primitive}. Options: {list(primitives.keys())}"}
    fn()
    obj = bpy.context.active_object
    if name:
        obj.name = name
    return {"name": obj.name, "type": obj.type, "location": list(obj.location)}


def _tool_delete_object(name=None):
    """Delete an object by name, or all selected objects."""
    if name:
        obj = bpy.data.objects.get(name)
        if obj is None:
            return {"error": f"Object not found: {name}"}
        bpy.data.objects.remove(obj, do_unlink=True)
        return {"deleted": name}
    else:
        names = [o.name for o in bpy.context.selected_objects]
        bpy.ops.object.delete()
        return {"deleted": names}


def _tool_transform_object(name, location=None, rotation=None, scale=None):
    """Set transform of an object by name."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"error": f"Object not found: {name}"}
    if location is not None:
        obj.location = tuple(location)
    if rotation is not None:
        import math
        obj.rotation_euler = tuple(math.radians(r) for r in rotation)
    if scale is not None:
        obj.scale = tuple(scale)
    return {
        "name": obj.name,
        "location": list(obj.location),
        "rotation_deg": [round(r * 57.2958, 2) for r in obj.rotation_euler],
        "scale": list(obj.scale),
    }


def _tool_set_material(object_name, preset=None, color=None, metallic=None, roughness=None):
    """Apply or create material on an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.type != 'MESH':
        return {"error": f"Mesh object not found: {object_name}"}

    from ..utils import make_principled_material

    kwargs = {}
    if color:
        kwargs['base_color'] = tuple(color[:3])
    if metallic is not None:
        kwargs['metallic'] = metallic
    if roughness is not None:
        kwargs['roughness'] = roughness

    if preset:
        from .material_tools import PRESET_PARAMS
        params = PRESET_PARAMS.get(preset, {})
        kwargs.update(params)

    mat = make_principled_material(f"MCP_{object_name}", **kwargs)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return {"material": mat.name, "object": object_name}


def _tool_render(filepath=None, samples=None, engine=None, resolution=None):
    """Render the current scene."""
    scene = bpy.context.scene
    if engine:
        scene.render.engine = engine
    if samples and scene.render.engine == 'CYCLES':
        scene.cycles.samples = samples
    if resolution:
        scene.render.resolution_x = resolution[0]
        scene.render.resolution_y = resolution[1]
    if filepath:
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        return {"rendered": filepath}
    else:
        bpy.ops.render.render()
        return {"rendered": "viewport"}


def _tool_import_model(filepath, format=None):
    """Import a 3D model file."""
    ext = os.path.splitext(filepath)[1].lower() if not format else f".{format}"
    importers = {
        '.obj': lambda: bpy.ops.wm.obj_import(filepath=filepath),
        '.fbx': lambda: bpy.ops.import_scene.fbx(filepath=filepath),
        '.gltf': lambda: bpy.ops.import_scene.gltf(filepath=filepath),
        '.glb': lambda: bpy.ops.import_scene.gltf(filepath=filepath),
        '.stl': lambda: bpy.ops.wm.stl_import(filepath=filepath),
    }
    fn = importers.get(ext)
    if fn is None:
        return {"error": f"Unsupported format: {ext}"}
    fn()
    imported = [o.name for o in bpy.context.selected_objects]
    return {"imported": imported, "count": len(imported)}


def _tool_export_model(filepath, format=None, selected_only=False):
    """Export scene or selected objects."""
    ext = os.path.splitext(filepath)[1].lower() if not format else f".{format}"
    exporters = {
        '.obj': lambda: bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=selected_only),
        '.fbx': lambda: bpy.ops.export_scene.fbx(filepath=filepath, use_selection=selected_only),
        '.glb': lambda: bpy.ops.export_scene.gltf(filepath=filepath, export_format='GLB', use_selection=selected_only),
        '.gltf': lambda: bpy.ops.export_scene.gltf(filepath=filepath, export_format='GLTF_SEPARATE', use_selection=selected_only),
        '.stl': lambda: bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=selected_only),
        '.usd': lambda: bpy.ops.wm.usd_export(filepath=filepath),
    }
    fn = exporters.get(ext)
    if fn is None:
        return {"error": f"Unsupported format: {ext}"}
    fn()
    return {"exported": filepath}


def _tool_execute_python(code):
    """Execute arbitrary Python code in Blender. Returns stdout output."""
    import io, sys
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        exec(code, {"bpy": bpy, "__builtins__": __builtins__})
        output = buffer.getvalue()
        return {"output": output, "success": True}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc(), "success": False}
    finally:
        sys.stdout = old_stdout


def _tool_setup_scene(lighting=None, camera=None, environment=None):
    """Set up a complete scene using RECA presets."""
    results = {}
    if lighting:
        bpy.context.scene.reca_scene_builder.lighting_preset = lighting
        bpy.ops.reca.setup_lighting()
        results['lighting'] = lighting
    if camera:
        bpy.context.scene.reca_scene_builder.camera_preset = camera
        bpy.ops.reca.setup_camera()
        results['camera'] = camera
    if environment:
        bpy.context.scene.reca_scene_builder.env_preset = environment
        bpy.ops.reca.setup_environment()
        results['environment'] = environment
    return results


def _tool_generate_procedural(generator, seed=42, **params):
    """Run a RECA procedural generator."""
    pg = bpy.context.scene.reca_procedural_gen
    pg.gen_type = generator.upper()
    pg.seed = seed
    for key, val in params.items():
        if hasattr(pg, key):
            setattr(pg, key, val)
    bpy.ops.reca.proc_generate()
    return {"generated": generator, "seed": seed}


def _tool_add_modifier(object_name, modifier_type, **params):
    """Add a modifier to an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"error": f"Object not found: {object_name}"}
    mod = obj.modifiers.new(name=f"RECA_{modifier_type}", type=modifier_type.upper())
    for key, val in params.items():
        if hasattr(mod, key):
            setattr(mod, key, val)
    return {"modifier": mod.name, "type": mod.type, "object": object_name}


def _tool_add_light(name="MCP_Light", type="AREA", location=None,
                    energy=100, color=None, size=1.0):
    """Add a light to the scene."""
    loc = tuple(location) if location else (0, 0, 5)
    col = tuple(color) if color else (1, 1, 1)
    bpy.ops.object.light_add(type=type.upper(), location=loc)
    light = bpy.context.active_object
    light.name = name
    light.data.energy = energy
    light.data.color = col
    if hasattr(light.data, 'size'):
        light.data.size = size
    return {"name": light.name, "type": type, "energy": energy}


def _tool_add_camera(name="MCP_Camera", location=None, lens=50, look_at=None):
    """Add a camera to the scene."""
    import math
    loc = tuple(location) if location else (7, -6, 5)
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.name = name
    cam.data.lens = lens
    bpy.context.scene.camera = cam

    if look_at:
        from mathutils import Vector
        target = Vector(look_at)
        direction = target - cam.location
        rot = direction.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot.to_euler()

    return {"name": cam.name, "lens": lens, "location": list(cam.location)}


def _tool_keyframe(object_name, data_path, frame, value=None):
    """Insert a keyframe on an object property."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"error": f"Object not found: {object_name}"}
    if value is not None:
        # Set value
        parts = data_path.split('.')
        target = obj
        for p in parts[:-1]:
            target = getattr(target, p)
        setattr(target, parts[-1], value)
    obj.keyframe_insert(data_path=data_path, frame=frame)
    return {"object": object_name, "data_path": data_path, "frame": frame}


# ─────────────────────────────────────────────
#  MCP Tool Registry
# ─────────────────────────────────────────────

MCP_TOOLS = {
    "scene_info": {
        "description": "Get scene statistics (objects, vertices, materials count)",
        "parameters": {},
        "handler": _tool_scene_info,
    },
    "list_objects": {
        "description": "List all objects in the scene with their properties",
        "parameters": {
            "type_filter": {"type": "string", "description": "Filter by type: MESH, LIGHT, CAMERA, etc.", "required": False},
        },
        "handler": _tool_list_objects,
    },
    "add_object": {
        "description": "Add a primitive object (cube, sphere, cylinder, plane, cone, torus, ico_sphere, monkey)",
        "parameters": {
            "primitive": {"type": "string", "description": "Primitive type", "required": True},
            "size": {"type": "number", "description": "Size of the object", "required": False},
            "location": {"type": "array", "description": "[x, y, z] position", "required": False},
            "name": {"type": "string", "description": "Object name", "required": False},
        },
        "handler": _tool_add_object,
    },
    "delete_object": {
        "description": "Delete an object by name",
        "parameters": {
            "name": {"type": "string", "description": "Object name to delete", "required": False},
        },
        "handler": _tool_delete_object,
    },
    "transform_object": {
        "description": "Set location, rotation (degrees), or scale of an object",
        "parameters": {
            "name": {"type": "string", "description": "Object name", "required": True},
            "location": {"type": "array", "description": "[x, y, z]", "required": False},
            "rotation": {"type": "array", "description": "[rx, ry, rz] in degrees", "required": False},
            "scale": {"type": "array", "description": "[sx, sy, sz]", "required": False},
        },
        "handler": _tool_transform_object,
    },
    "set_material": {
        "description": "Apply a material to an object (preset or custom color)",
        "parameters": {
            "object_name": {"type": "string", "required": True},
            "preset": {"type": "string", "description": "RECA preset: METAL_GOLD, GLASS_CLEAR, etc.", "required": False},
            "color": {"type": "array", "description": "[r, g, b] 0-1 range", "required": False},
            "metallic": {"type": "number", "required": False},
            "roughness": {"type": "number", "required": False},
        },
        "handler": _tool_set_material,
    },
    "render": {
        "description": "Render the scene to an image file",
        "parameters": {
            "filepath": {"type": "string", "required": False},
            "samples": {"type": "integer", "required": False},
            "engine": {"type": "string", "description": "CYCLES or BLENDER_EEVEE_NEXT", "required": False},
            "resolution": {"type": "array", "description": "[width, height]", "required": False},
        },
        "handler": _tool_render,
    },
    "import_model": {
        "description": "Import a 3D model file (OBJ, FBX, glTF, STL)",
        "parameters": {
            "filepath": {"type": "string", "required": True},
            "format": {"type": "string", "required": False},
        },
        "handler": _tool_import_model,
    },
    "export_model": {
        "description": "Export scene or selection to 3D file",
        "parameters": {
            "filepath": {"type": "string", "required": True},
            "format": {"type": "string", "required": False},
            "selected_only": {"type": "boolean", "required": False},
        },
        "handler": _tool_export_model,
    },
    "execute_python": {
        "description": "Execute arbitrary Python code in Blender's environment",
        "parameters": {
            "code": {"type": "string", "description": "Python code to execute", "required": True},
        },
        "handler": _tool_execute_python,
    },
    "setup_scene": {
        "description": "Set up scene with RECA presets (lighting, camera, environment)",
        "parameters": {
            "lighting": {"type": "string", "description": "STUDIO_3POINT, DRAMATIC, PRODUCT, SUNSET, NEON, etc.", "required": False},
            "camera": {"type": "string", "description": "PERSPECTIVE, PORTRAIT, WIDE, CINEMATIC, etc.", "required": False},
            "environment": {"type": "string", "description": "INFINITE_FLOOR, CYCLORAMA, GRADIENT_BG, TURNTABLE", "required": False},
        },
        "handler": _tool_setup_scene,
    },
    "generate_procedural": {
        "description": "Generate procedural geometry (BUILDING, TERRAIN, TREE, ROCKS, CITY, PIPE, etc.)",
        "parameters": {
            "generator": {"type": "string", "required": True},
            "seed": {"type": "integer", "required": False},
        },
        "handler": _tool_generate_procedural,
    },
    "add_modifier": {
        "description": "Add a modifier to an object (SUBSURF, MIRROR, ARRAY, BEVEL, SOLIDIFY, etc.)",
        "parameters": {
            "object_name": {"type": "string", "required": True},
            "modifier_type": {"type": "string", "required": True},
        },
        "handler": _tool_add_modifier,
    },
    "add_light": {
        "description": "Add a light to the scene",
        "parameters": {
            "name": {"type": "string", "required": False},
            "type": {"type": "string", "description": "AREA, POINT, SUN, SPOT", "required": False},
            "location": {"type": "array", "required": False},
            "energy": {"type": "number", "required": False},
            "color": {"type": "array", "description": "[r, g, b]", "required": False},
            "size": {"type": "number", "required": False},
        },
        "handler": _tool_add_light,
    },
    "add_camera": {
        "description": "Add a camera to the scene",
        "parameters": {
            "name": {"type": "string", "required": False},
            "location": {"type": "array", "required": False},
            "lens": {"type": "number", "required": False},
            "look_at": {"type": "array", "description": "[x, y, z] target point", "required": False},
        },
        "handler": _tool_add_camera,
    },
    "keyframe": {
        "description": "Insert a keyframe on an object property for animation",
        "parameters": {
            "object_name": {"type": "string", "required": True},
            "data_path": {"type": "string", "description": "e.g. location, rotation_euler, scale", "required": True},
            "frame": {"type": "integer", "required": True},
            "value": {"description": "Value to set before keyframing", "required": False},
        },
        "handler": _tool_keyframe,
    },
}


# ─────────────────────────────────────────────
#  MCP JSON-RPC Protocol Handler
# ─────────────────────────────────────────────

def _build_tool_schema():
    """Build MCP tools/list response."""
    tools = []
    for name, spec in MCP_TOOLS.items():
        properties = {}
        required = []
        for pname, pspec in spec["parameters"].items():
            properties[pname] = {
                "type": pspec.get("type", "string"),
                "description": pspec.get("description", ""),
            }
            if pspec.get("required", False):
                required.append(pname)
        tools.append({
            "name": name,
            "description": spec["description"],
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })
    return tools


def handle_mcp_request(request):
    """Process a JSON-RPC 2.0 MCP request and return a response."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "reca-blender-mcp",
                    "version": "1.0.0",
                },
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": _build_tool_schema()},
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        spec = MCP_TOOLS.get(tool_name)
        if spec is None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
            }

        # Execute on main thread
        result = _queue_blender_call(spec["handler"], arguments)

        if "error" in result and "result" not in result:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": True,
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result.get("result", result))}],
            },
        }

    elif method == "notifications/initialized":
        return None  # No response for notifications

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }


# ─────────────────────────────────────────────
#  HTTP Server
# ─────────────────────────────────────────────

class MCPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            request = json.loads(body)
            response = handle_mcp_request(request)
            if response is None:
                self.send_response(204)
                self.end_headers()
                return
            response_body = json.dumps(response).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as e:
            error_response = json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(e)},
            }).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response)

    def do_GET(self):
        """Health check and tool listing endpoint."""
        if self.path == '/health':
            body = json.dumps({"status": "ok", "server": "reca-blender-mcp"}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/tools':
            body = json.dumps({"tools": _build_tool_schema()}, indent=2).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default logging


_server_instance = None
_server_thread = None


def start_server(port=9876):
    """Start the MCP HTTP server."""
    global _server_instance, _server_thread

    if _server_instance is not None:
        return False

    _server_instance = HTTPServer(('127.0.0.1', port), MCPRequestHandler)
    _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
    _server_thread.start()

    # Register the queue processor timer
    if not bpy.app.timers.is_registered(_process_queue):
        bpy.app.timers.register(_process_queue, persistent=True)

    return True


def stop_server():
    """Stop the MCP HTTP server."""
    global _server_instance, _server_thread

    if _server_instance is not None:
        _server_instance.shutdown()
        _server_instance = None
        _server_thread = None

    if bpy.app.timers.is_registered(_process_queue):
        bpy.app.timers.unregister(_process_queue)

    return True


def is_server_running():
    return _server_instance is not None


# ─────────────────────────────────────────────
#  MCP Config Generator
# ─────────────────────────────────────────────

def generate_mcp_config(port=9876, agent="openclaw"):
    """Generate MCP client config JSON for various AI agents."""
    base_config = {
        "mcpServers": {
            "reca-blender": {
                "url": f"http://127.0.0.1:{port}",
                "transport": "http",
            }
        }
    }

    configs = {
        "openclaw": {
            "path": "~/.openclaw/mcp.json",
            "config": base_config,
        },
        "claude-code": {
            "path": ".claude/mcp.json",
            "config": base_config,
        },
        "cursor": {
            "path": ".cursor/mcp.json",
            "config": base_config,
        },
        "codex": {
            "path": ".agents/mcp.json",
            "config": base_config,
        },
    }

    return configs.get(agent, configs["openclaw"])


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_mcp_server(PropertyGroup):
    enabled: BoolProperty(name="Server Enabled", default=False)
    port: IntProperty(name="Port", default=9876, min=1024, max=65535)
    auto_start: BoolProperty(name="Auto-Start on Blender Launch", default=False)
    agent_type: EnumProperty(
        name="Agent",
        items=[
            ('OPENCLAW', "OpenClaw.ai", "OpenClaw AI agent"),
            ('CLAUDE_CODE', "Claude Code", "Anthropic Claude Code"),
            ('CURSOR', "Cursor", "Cursor AI IDE"),
            ('CODEX', "Codex", "OpenAI Codex"),
            ('CUSTOM', "Custom", "Custom MCP client"),
        ],
        default='OPENCLAW',
    )
    status: StringProperty(name="Status", default="Stopped")
    allow_python_exec: BoolProperty(
        name="Allow Python Execution",
        description="Allow AI agents to execute arbitrary Python code (security risk!)",
        default=False,
    )


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_mcp_start(Operator):
    """Start the MCP server for AI agent control"""
    bl_idname = "reca.mcp_start"
    bl_label = "Start MCP Server"

    def execute(self, context):
        mcp = context.scene.reca_mcp
        if is_server_running():
            self.report({'WARNING'}, "MCP server already running")
            return {'CANCELLED'}

        # Remove execute_python if not allowed
        if not mcp.allow_python_exec and "execute_python" in MCP_TOOLS:
            MCP_TOOLS.pop("execute_python", None)

        if start_server(mcp.port):
            mcp.enabled = True
            mcp.status = f"Running on port {mcp.port}"
            self.report({'INFO'}, f"MCP server started on http://127.0.0.1:{mcp.port}")
        else:
            self.report({'ERROR'}, "Failed to start MCP server")
        return {'FINISHED'}


class RECA_OT_mcp_stop(Operator):
    """Stop the MCP server"""
    bl_idname = "reca.mcp_stop"
    bl_label = "Stop MCP Server"

    def execute(self, context):
        mcp = context.scene.reca_mcp
        stop_server()
        mcp.enabled = False
        mcp.status = "Stopped"
        self.report({'INFO'}, "MCP server stopped")
        return {'FINISHED'}


class RECA_OT_mcp_generate_config(Operator):
    """Generate MCP config file for the selected AI agent"""
    bl_idname = "reca.mcp_generate_config"
    bl_label = "Generate Config"

    def execute(self, context):
        mcp = context.scene.reca_mcp
        agent_map = {
            'OPENCLAW': 'openclaw',
            'CLAUDE_CODE': 'claude-code',
            'CURSOR': 'cursor',
            'CODEX': 'codex',
            'CUSTOM': 'openclaw',
        }
        agent = agent_map[mcp.agent_type]
        config = generate_mcp_config(mcp.port, agent)

        # Save to clipboard-friendly format
        config_json = json.dumps(config["config"], indent=2)
        context.window_manager.clipboard = config_json

        self.report({'INFO'}, f"MCP config copied to clipboard. Save to: {config['path']}")
        return {'FINISHED'}


class RECA_OT_mcp_test(Operator):
    """Send a test request to the MCP server"""
    bl_idname = "reca.mcp_test"
    bl_label = "Test Connection"

    def execute(self, context):
        import urllib.request
        mcp = context.scene.reca_mcp
        try:
            url = f"http://127.0.0.1:{mcp.port}/health"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                if data.get("status") == "ok":
                    self.report({'INFO'}, "MCP server is healthy!")
                else:
                    self.report({'WARNING'}, f"Unexpected response: {data}")
        except Exception as e:
            self.report({'ERROR'}, f"Connection failed: {e}")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    mcp = context.scene.reca_mcp

    box = layout.box()
    box.label(text="MCP Server", icon='URL')

    # Status
    row = box.row()
    if is_server_running():
        row.label(text=mcp.status, icon='CHECKMARK')
    else:
        row.label(text="Stopped", icon='CANCEL')

    # Server controls
    box.prop(mcp, "port")
    box.prop(mcp, "auto_start")
    box.prop(mcp, "allow_python_exec")

    row = box.row(align=True)
    row.scale_y = 1.3
    if is_server_running():
        row.operator("reca.mcp_stop", icon='PAUSE', text="Stop Server")
        row.operator("reca.mcp_test", icon='PLAY', text="Test")
    else:
        row.operator("reca.mcp_start", icon='PLAY', text="Start Server")

    # Agent config
    layout.separator()
    box = layout.box()
    box.label(text="AI Agent Config", icon='GHOST_ENABLED')
    box.prop(mcp, "agent_type")
    box.operator("reca.mcp_generate_config", icon='COPYDOWN')

    # Available tools
    layout.separator()
    box = layout.box()
    box.label(text=f"Available Tools ({len(MCP_TOOLS)})", icon='TOOL_SETTINGS')
    col = box.column(align=True)
    for name, spec in MCP_TOOLS.items():
        row = col.row()
        row.label(text=name, icon='DOT')
        row.label(text=spec["description"][:40])

    # Connection info
    if is_server_running():
        layout.separator()
        box = layout.box()
        box.label(text="Connection Info", icon='INFO')
        box.label(text=f"URL: http://127.0.0.1:{mcp.port}")
        box.label(text=f"Health: http://127.0.0.1:{mcp.port}/health")
        box.label(text=f"Tools: http://127.0.0.1:{mcp.port}/tools")


# ─────────────────────────────────────────────
#  Auto-start handler
# ─────────────────────────────────────────────

def _auto_start_handler(dummy):
    """Start MCP server automatically if configured."""
    for scene in bpy.data.scenes:
        if hasattr(scene, 'reca_mcp') and scene.reca_mcp.auto_start:
            start_server(scene.reca_mcp.port)
            scene.reca_mcp.enabled = True
            scene.reca_mcp.status = f"Running on port {scene.reca_mcp.port}"
            break


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_mcp_server,
    RECA_OT_mcp_start,
    RECA_OT_mcp_stop,
    RECA_OT_mcp_generate_config,
    RECA_OT_mcp_test,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_mcp = PointerProperty(type=RECA_PG_mcp_server)
    bpy.app.handlers.load_post.append(_auto_start_handler)


def unregister():
    stop_server()
    bpy.app.handlers.load_post.remove(_auto_start_handler)
    del bpy.types.Scene.reca_mcp
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
