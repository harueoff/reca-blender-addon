# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA MCP Server — Model Context Protocol server for AI agent control.

Exposes Blender operations as MCP tools so AI agents (OpenClaw, Claude Code,
Codex, Cursor, etc.) can control Blender programmatically.

Supports TWO connection modes:
  1. TCP Socket (port 9876) — compatible with `uvx blender-mcp` ecosystem
     Claude Desktop / Cursor → uvx blender-mcp → TCP socket → RECA
  2. HTTP Server (port 9877) — direct JSON-RPC 2.0 MCP over HTTP
     Any HTTP client → http://127.0.0.1:9877 → RECA

Architecture:
  - All Blender operations are queued and executed on the main thread
    via bpy.app.timers (Blender doesn't allow bpy calls from threads)
  - TCP/HTTP servers run in background daemon threads
"""

import bpy
import json
import io
import os
import sys
import math
import socket
import struct
import threading
import queue
import traceback
from contextlib import redirect_stdout
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
    event.wait(timeout=60)
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
#  MCP Tool Implementations
# ─────────────────────────────────────────────

def _tool_scene_info():
    """Get current scene statistics."""
    scene = bpy.context.scene
    objects = list(bpy.data.objects)
    meshes = [o for o in objects if o.type == 'MESH']
    total_verts = sum(len(o.data.vertices) for o in meshes if o.data)
    total_faces = sum(len(o.data.polygons) for o in meshes if o.data)
    return {
        "scene_name": scene.name,
        "object_count": len(objects),
        "mesh_count": len(meshes),
        "total_vertices": total_verts,
        "total_faces": total_faces,
        "materials": len(bpy.data.materials),
        "render_engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "frame_current": scene.frame_current,
        "frame_range": [scene.frame_start, scene.frame_end],
    }


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
        "sphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=size / 2, location=loc),
        "cylinder": lambda: bpy.ops.mesh.primitive_cylinder_add(radius=size / 2, depth=size, location=loc),
        "plane": lambda: bpy.ops.mesh.primitive_plane_add(size=size, location=loc),
        "cone": lambda: bpy.ops.mesh.primitive_cone_add(radius1=size / 2, depth=size, location=loc),
        "torus": lambda: bpy.ops.mesh.primitive_torus_add(major_radius=size, minor_radius=size * 0.3, location=loc),
        "ico_sphere": lambda: bpy.ops.mesh.primitive_ico_sphere_add(radius=size / 2, location=loc),
        "monkey": lambda: bpy.ops.mesh.primitive_monkey_add(size=size, location=loc),
        "empty": lambda: bpy.ops.object.empty_add(location=loc),
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
        obj.rotation_euler = tuple(math.radians(r) for r in rotation)
    if scale is not None:
        obj.scale = tuple(scale)
    return {
        "name": obj.name,
        "location": list(obj.location),
        "rotation_deg": [round(math.degrees(r), 2) for r in obj.rotation_euler],
        "scale": list(obj.scale),
    }


def _tool_set_material(object_name, preset=None, color=None, metallic=None,
                       roughness=None, emission_color=None, emission_strength=None):
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
    if emission_color:
        kwargs['emission_color'] = tuple(emission_color[:3])
    if emission_strength is not None:
        kwargs['emission_strength'] = emission_strength

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
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        exec(code, {"bpy": bpy, "mathutils": __import__('mathutils'), "__builtins__": __builtins__})
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
        parts = data_path.split('.')
        target = obj
        for p in parts[:-1]:
            target = getattr(target, p)
        setattr(target, parts[-1], value)
    obj.keyframe_insert(data_path=data_path, frame=frame)
    return {"object": object_name, "data_path": data_path, "frame": frame}


def _tool_get_object_info(name):
    """Get detailed information about a specific object."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"error": f"Object not found: {name}"}
    info = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "rotation_deg": [round(math.degrees(r), 2) for r in obj.rotation_euler],
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "visible": obj.visible_get(),
        "parent": obj.parent.name if obj.parent else None,
        "children": [c.name for c in obj.children],
    }
    if obj.type == 'MESH' and obj.data:
        info["vertices"] = len(obj.data.vertices)
        info["edges"] = len(obj.data.edges)
        info["faces"] = len(obj.data.polygons)
        info["materials"] = [m.name for m in obj.data.materials if m]
    if obj.modifiers:
        info["modifiers"] = [{"name": m.name, "type": m.type} for m in obj.modifiers]
    return info


def _tool_set_render_settings(engine=None, samples=None, resolution=None,
                              output_path=None, file_format=None):
    """Configure render settings."""
    scene = bpy.context.scene
    if engine:
        scene.render.engine = engine
    if samples:
        if scene.render.engine == 'CYCLES':
            scene.cycles.samples = samples
        else:
            scene.eevee.taa_render_samples = samples
    if resolution:
        scene.render.resolution_x = resolution[0]
        scene.render.resolution_y = resolution[1]
    if output_path:
        scene.render.filepath = output_path
    if file_format:
        scene.render.image_settings.file_format = file_format.upper()
    return {
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    }


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
    "get_object_info": {
        "description": "Get detailed info about a specific object (vertices, materials, modifiers, children)",
        "parameters": {
            "name": {"type": "string", "description": "Object name", "required": True},
        },
        "handler": _tool_get_object_info,
    },
    "add_object": {
        "description": "Add a primitive object (cube, sphere, cylinder, plane, cone, torus, ico_sphere, monkey, empty)",
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
        "description": "Apply a material to an object (preset or custom color/PBR)",
        "parameters": {
            "object_name": {"type": "string", "required": True},
            "preset": {"type": "string", "description": "RECA preset: METAL_GOLD, GLASS_CLEAR, etc.", "required": False},
            "color": {"type": "array", "description": "[r, g, b] 0-1 range", "required": False},
            "metallic": {"type": "number", "required": False},
            "roughness": {"type": "number", "required": False},
            "emission_color": {"type": "array", "description": "[r, g, b]", "required": False},
            "emission_strength": {"type": "number", "required": False},
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
    "set_render_settings": {
        "description": "Configure render engine, samples, resolution, output path, file format",
        "parameters": {
            "engine": {"type": "string", "required": False},
            "samples": {"type": "integer", "required": False},
            "resolution": {"type": "array", "required": False},
            "output_path": {"type": "string", "required": False},
            "file_format": {"type": "string", "description": "PNG, JPEG, EXR, etc.", "required": False},
        },
        "handler": _tool_set_render_settings,
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
            "lighting": {"type": "string", "description": "STUDIO_3POINT, DRAMATIC, NEON, GOLDEN_HOUR, etc.", "required": False},
            "camera": {"type": "string", "description": "FRONT, THREE_QUARTER, TOP_DOWN, LOW_ANGLE, etc.", "required": False},
            "environment": {"type": "string", "description": "INFINITE, GROUND, ROOM, PEDESTAL, GRADIENT", "required": False},
        },
        "handler": _tool_setup_scene,
    },
    "generate_procedural": {
        "description": "Generate procedural geometry (BUILDING, TERRAIN, TREE, ROCKS, CITY, ARRAY_PATTERN, SCATTER, PIPE)",
        "parameters": {
            "generator": {"type": "string", "required": True},
            "seed": {"type": "integer", "required": False},
        },
        "handler": _tool_generate_procedural,
    },
    "add_modifier": {
        "description": "Add a modifier to an object (SUBSURF, MIRROR, ARRAY, BEVEL, SOLIDIFY, BOOLEAN, etc.)",
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
#  TCP Socket Server (blender-mcp compatible)
# ─────────────────────────────────────────────

class BlenderMCPSocketServer:
    """TCP socket server compatible with ahujasid/blender-mcp protocol.

    Protocol: JSON commands over TCP socket.
    Command format:  {"type": "command_name", "params": {...}}
    Response format: {"status": "success|error", "result": ..., "message": ...}
    """

    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.server_thread = None

    def start(self):
        if self.running:
            return False
        self.running = True
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            self.server_thread = threading.Thread(target=self._serve, daemon=True)
            self.server_thread.start()
            return True
        except Exception as e:
            print(f"[RECA MCP] Socket server error: {e}")
            self.running = False
            return False

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
        self.server_thread = None

    def _serve(self):
        print(f"[RECA MCP] TCP socket server listening on {self.host}:{self.port}")
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                handler = threading.Thread(
                    target=self._handle_client, args=(client, addr), daemon=True
                )
                handler.start()
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    traceback.print_exc()
                break

    def _handle_client(self, client, addr):
        """Handle a connected client — read JSON commands, send responses."""
        print(f"[RECA MCP] Client connected: {addr}")
        buffer = ""
        try:
            client.settimeout(None)
            while self.running:
                data = client.recv(8192)
                if not data:
                    break
                buffer += data.decode('utf-8', errors='replace')

                # Process complete JSON messages
                while buffer:
                    buffer = buffer.strip()
                    if not buffer:
                        break
                    try:
                        command = json.loads(buffer)
                        buffer = ""
                    except json.JSONDecodeError:
                        # Try to find a complete JSON object
                        depth = 0
                        in_string = False
                        escape = False
                        end_pos = -1
                        for i, ch in enumerate(buffer):
                            if escape:
                                escape = False
                                continue
                            if ch == '\\' and in_string:
                                escape = True
                                continue
                            if ch == '"':
                                in_string = not in_string
                                continue
                            if in_string:
                                continue
                            if ch == '{':
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                                if depth == 0:
                                    end_pos = i + 1
                                    break
                        if end_pos == -1:
                            break  # Need more data
                        try:
                            command = json.loads(buffer[:end_pos])
                            buffer = buffer[end_pos:]
                        except json.JSONDecodeError:
                            break

                    # Process command
                    response = self._handle_command(command)
                    response_json = json.dumps(response) + "\n"
                    client.sendall(response_json.encode('utf-8'))

        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception:
            traceback.print_exc()
        finally:
            try:
                client.close()
            except Exception:
                pass
            print(f"[RECA MCP] Client disconnected: {addr}")

    def _handle_command(self, command):
        """Handle a blender-mcp style command.

        Compatible commands from blender-mcp:
        - get_scene_info, list_objects, create_object, modify_object, delete_object
        - set_material, execute_code, get_polyhaven_categories, etc.
        Plus all RECA-specific tools.
        """
        cmd_type = command.get("type", "")
        params = command.get("params", {})

        try:
            # Map blender-mcp command names to RECA tool handlers
            handler_map = {
                # blender-mcp compatible commands
                "get_scene_info": ("scene_info", {}),
                "list_objects": ("list_objects", params),
                "get_object_info": ("get_object_info", params),
                "create_object": ("add_object", self._map_create_params(params)),
                "modify_object": ("transform_object", self._map_modify_params(params)),
                "delete_object": ("delete_object", params),
                "set_material": ("set_material", self._map_material_params(params)),
                "execute_code": ("execute_python", {"code": params.get("code", "")}),
                "render": ("render", params),
                # Direct RECA tool access (use tool name as command type)
                "scene_info": ("scene_info", {}),
                "add_object": ("add_object", params),
                "transform_object": ("transform_object", params),
                "set_render_settings": ("set_render_settings", params),
                "import_model": ("import_model", params),
                "export_model": ("export_model", params),
                "execute_python": ("execute_python", params),
                "setup_scene": ("setup_scene", params),
                "generate_procedural": ("generate_procedural", params),
                "add_modifier": ("add_modifier", params),
                "add_light": ("add_light", params),
                "add_camera": ("add_camera", params),
                "keyframe": ("keyframe", params),
            }

            if cmd_type == "ping":
                return {"status": "success", "result": "pong"}

            if cmd_type not in handler_map:
                # Try direct tool lookup
                spec = MCP_TOOLS.get(cmd_type)
                if spec:
                    result = _queue_blender_call(spec["handler"], params)
                    if "error" in result and "result" not in result:
                        return {"status": "error", "message": result.get("error", "Unknown error")}
                    return {"status": "success", "result": result.get("result", result)}
                return {"status": "error", "message": f"Unknown command: {cmd_type}"}

            tool_name, mapped_params = handler_map[cmd_type]
            spec = MCP_TOOLS.get(tool_name)
            if not spec:
                return {"status": "error", "message": f"Tool not found: {tool_name}"}

            result = _queue_blender_call(spec["handler"], mapped_params)
            if "error" in result and "result" not in result:
                return {"status": "error", "message": result.get("error", "Unknown error")}
            return {"status": "success", "result": result.get("result", result)}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _map_create_params(self, params):
        """Map blender-mcp create_object params to RECA add_object params."""
        mapped = {}
        if "type" in params:
            mapped["primitive"] = params["type"].lower()
        if "name" in params:
            mapped["name"] = params["name"]
        if "location" in params:
            mapped["location"] = params["location"]
        if "size" in params:
            mapped["size"] = params["size"]
        elif "scale" in params:
            s = params["scale"]
            if isinstance(s, list):
                mapped["size"] = s[0] if s else 1.0
            else:
                mapped["size"] = s
        return mapped

    def _map_modify_params(self, params):
        """Map blender-mcp modify_object params to RECA transform_object params."""
        mapped = {"name": params.get("name", params.get("object_name", ""))}
        if "location" in params:
            mapped["location"] = params["location"]
        if "rotation" in params:
            mapped["rotation"] = params["rotation"]
        if "scale" in params:
            mapped["scale"] = params["scale"]
        return mapped

    def _map_material_params(self, params):
        """Map blender-mcp set_material params to RECA set_material params."""
        mapped = {"object_name": params.get("object_name", params.get("name", ""))}
        if "color" in params:
            mapped["color"] = params["color"]
        if "metallic" in params:
            mapped["metallic"] = params["metallic"]
        if "roughness" in params:
            mapped["roughness"] = params["roughness"]
        if "preset" in params:
            mapped["preset"] = params["preset"]
        return mapped


# ─────────────────────────────────────────────
#  MCP JSON-RPC Protocol Handler (HTTP mode)
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
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "reca-blender-mcp", "version": "2.0.0"},
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
        return None

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
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": str(e)},
            }).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response)

    def do_GET(self):
        if self.path == '/health':
            body = json.dumps({"status": "ok", "server": "reca-blender-mcp", "version": "2.0.0"}).encode()
        elif self.path == '/tools':
            body = json.dumps({"tools": _build_tool_schema()}, indent=2).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


# ─────────────────────────────────────────────
#  Server Lifecycle
# ─────────────────────────────────────────────

_socket_server = None
_http_server = None
_http_thread = None


def _get_local_ip():
    """Get the machine's local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "0.0.0.0"


def start_servers(socket_port=9876, http_port=9877, remote=False):
    """Start both TCP socket and HTTP servers."""
    global _socket_server, _http_server, _http_thread

    # Register timer
    if not bpy.app.timers.is_registered(_process_queue):
        bpy.app.timers.register(_process_queue, persistent=True)

    bind_host = '0.0.0.0' if remote else 'localhost'
    results = {}

    # Start TCP socket (blender-mcp compatible)
    if _socket_server is None:
        _socket_server = BlenderMCPSocketServer(bind_host, socket_port)
        if _socket_server.start():
            results['socket'] = f"{bind_host}:{socket_port}"
        else:
            _socket_server = None
            results['socket_error'] = "Failed to start"

    # Start HTTP (direct MCP)
    if _http_server is None:
        try:
            _http_server = HTTPServer((bind_host, http_port), MCPRequestHandler)
            _http_thread = threading.Thread(target=_http_server.serve_forever, daemon=True)
            _http_thread.start()
            results['http'] = f"http://{bind_host}:{http_port}"
        except Exception as e:
            _http_server = None
            results['http_error'] = str(e)

    if remote:
        results['local_ip'] = _get_local_ip()

    return results


def stop_servers():
    """Stop all servers."""
    global _socket_server, _http_server, _http_thread

    if _socket_server:
        _socket_server.stop()
        _socket_server = None

    if _http_server:
        _http_server.shutdown()
        _http_server = None
        _http_thread = None

    if bpy.app.timers.is_registered(_process_queue):
        bpy.app.timers.unregister(_process_queue)


def is_server_running():
    return _socket_server is not None or _http_server is not None


def is_socket_running():
    return _socket_server is not None and _socket_server.running


def is_http_running():
    return _http_server is not None


# ─────────────────────────────────────────────
#  MCP Config Generator
# ─────────────────────────────────────────────

def generate_mcp_config(socket_port=9876, http_port=9877, agent="claude-desktop", host="127.0.0.1"):
    """Generate MCP client config JSON for various AI agents."""
    configs = {
        "claude-desktop": {
            "description": "Claude Desktop (via uvx reca-blender-mcp)",
            "path": "claude_desktop_config.json",
            "config": {
                "mcpServers": {
                    "blender": {
                        "command": "uvx",
                        "args": ["reca-blender-mcp"],
                        "env": {
                            "BLENDER_HOST": host,
                            "BLENDER_PORT": str(socket_port),
                        },
                    }
                }
            },
        },
        "claude-code": {
            "description": "Claude Code CLI",
            "path": ".claude/mcp.json",
            "config": {
                "mcpServers": {
                    "reca-blender": {
                        "url": f"http://{host}:{http_port}",
                    }
                }
            },
        },
        "cursor": {
            "description": "Cursor AI IDE",
            "path": ".cursor/mcp.json",
            "config": {
                "mcpServers": {
                    "blender": {
                        "command": "uvx",
                        "args": ["reca-blender-mcp"],
                        "env": {
                            "BLENDER_HOST": host,
                            "BLENDER_PORT": str(socket_port),
                        },
                    }
                }
            },
        },
        "openclaw": {
            "description": "OpenClaw.ai",
            "path": "~/.openclaw/mcp.json",
            "config": {
                "mcpServers": {
                    "reca-blender": {
                        "url": f"http://{host}:{http_port}",
                    }
                }
            },
        },
        "direct-http": {
            "description": "Direct HTTP connection (any client)",
            "path": "mcp.json",
            "config": {
                "mcpServers": {
                    "reca-blender": {
                        "url": f"http://{host}:{http_port}",
                    }
                }
            },
        },
    }
    return configs.get(agent, configs["claude-desktop"])


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_mcp_server(PropertyGroup):
    enabled: BoolProperty(name="Server Enabled", default=False)
    socket_port: IntProperty(name="Socket Port (blender-mcp)", default=9876, min=1024, max=65535)
    http_port: IntProperty(name="HTTP Port (direct MCP)", default=9877, min=1024, max=65535)
    auto_start: BoolProperty(name="Auto-Start on Blender Launch", default=False)
    remote_access: BoolProperty(
        name="Remote Access (0.0.0.0)",
        description="Allow connections from other computers on the network. "
                    "When disabled, only localhost (127.0.0.1) can connect",
        default=False,
    )
    agent_type: EnumProperty(
        name="Agent",
        items=[
            ('CLAUDE_DESKTOP', "Claude Desktop", "Claude Desktop via uvx blender-mcp"),
            ('CLAUDE_CODE', "Claude Code", "Anthropic Claude Code CLI"),
            ('CURSOR', "Cursor", "Cursor AI IDE"),
            ('OPENCLAW', "OpenClaw.ai", "OpenClaw AI agent"),
            ('DIRECT_HTTP', "Direct HTTP", "Direct HTTP connection"),
        ],
        default='CLAUDE_DESKTOP',
    )
    status: StringProperty(name="Status", default="Stopped")
    local_ip: StringProperty(name="Local IP", default="")
    allow_python_exec: BoolProperty(
        name="Allow Python Execution",
        description="Allow AI agents to execute arbitrary Python code (security risk!)",
        default=False,
    )


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_mcp_start(Operator):
    """Start the MCP servers (TCP socket + HTTP)"""
    bl_idname = "reca.mcp_start"
    bl_label = "Start MCP Server"

    def execute(self, context):
        mcp = context.scene.reca_mcp
        if is_server_running():
            self.report({'WARNING'}, "MCP servers already running")
            return {'CANCELLED'}

        if not mcp.allow_python_exec:
            MCP_TOOLS.pop("execute_python", None)
        elif "execute_python" not in MCP_TOOLS:
            MCP_TOOLS["execute_python"] = {
                "description": "Execute arbitrary Python code in Blender's environment",
                "parameters": {"code": {"type": "string", "required": True}},
                "handler": _tool_execute_python,
            }

        results = start_servers(mcp.socket_port, mcp.http_port, remote=mcp.remote_access)
        mcp.enabled = True

        parts = []
        if 'socket' in results:
            parts.append(f"Socket: {results['socket']}")
        if 'http' in results:
            parts.append(f"HTTP: {results['http']}")
        if 'local_ip' in results:
            mcp.local_ip = results['local_ip']
        mcp.status = " | ".join(parts) if parts else "Error"

        bind = "0.0.0.0 (remote)" if mcp.remote_access else "localhost"
        msg = f"MCP started — {bind} — Socket :{mcp.socket_port} + HTTP :{mcp.http_port}"
        if mcp.remote_access and mcp.local_ip:
            msg += f" — LAN IP: {mcp.local_ip}"
        self.report({'INFO'}, msg)
        print(f"[RECA MCP] {msg}")
        return {'FINISHED'}


class RECA_OT_mcp_stop(Operator):
    """Stop all MCP servers"""
    bl_idname = "reca.mcp_stop"
    bl_label = "Stop MCP Server"

    def execute(self, context):
        mcp = context.scene.reca_mcp
        stop_servers()
        mcp.enabled = False
        mcp.status = "Stopped"
        self.report({'INFO'}, "MCP servers stopped")
        return {'FINISHED'}


class RECA_OT_mcp_generate_config(Operator):
    """Generate and copy MCP config for the selected AI agent"""
    bl_idname = "reca.mcp_generate_config"
    bl_label = "Copy Config to Clipboard"

    def execute(self, context):
        mcp = context.scene.reca_mcp
        agent_map = {
            'CLAUDE_DESKTOP': 'claude-desktop',
            'CLAUDE_CODE': 'claude-code',
            'CURSOR': 'cursor',
            'OPENCLAW': 'openclaw',
            'DIRECT_HTTP': 'direct-http',
        }
        agent = agent_map[mcp.agent_type]
        host = mcp.local_ip if mcp.remote_access and mcp.local_ip else "127.0.0.1"
        config = generate_mcp_config(mcp.socket_port, mcp.http_port, agent, host=host)

        config_json = json.dumps(config["config"], indent=2)
        context.window_manager.clipboard = config_json

        self.report({'INFO'}, f"Config copied! Save to: {config['path']}")
        return {'FINISHED'}


class RECA_OT_mcp_test(Operator):
    """Send a test request to the MCP server"""
    bl_idname = "reca.mcp_test"
    bl_label = "Test Connection"

    def execute(self, context):
        import urllib.request
        mcp = context.scene.reca_mcp
        results = []

        # Test socket
        if is_socket_running():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(('localhost', mcp.socket_port))
                s.sendall(json.dumps({"type": "ping"}).encode('utf-8'))
                resp = s.recv(4096).decode('utf-8')
                data = json.loads(resp)
                if data.get("status") == "success":
                    results.append(f"Socket :{mcp.socket_port} OK")
                s.close()
            except Exception as e:
                results.append(f"Socket error: {e}")

        # Test HTTP
        if is_http_running():
            try:
                url = f"http://127.0.0.1:{mcp.http_port}/health"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read())
                    if data.get("status") == "ok":
                        results.append(f"HTTP :{mcp.http_port} OK")
            except Exception as e:
                results.append(f"HTTP error: {e}")

        msg = " | ".join(results) if results else "No servers running"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    mcp = context.scene.reca_mcp

    # Server Status
    box = layout.box()
    row = box.row()
    row.label(text="MCP Server", icon='URL')
    if is_server_running():
        row.label(text="RUNNING", icon='CHECKMARK')
    else:
        row.label(text="STOPPED", icon='CANCEL')

    # Connection status details
    if is_server_running():
        col = box.column(align=True)
        host = mcp.local_ip if mcp.remote_access and mcp.local_ip else "localhost"
        if is_socket_running():
            col.label(text=f"Socket: {host}:{mcp.socket_port} (blender-mcp)", icon='LINKED')
        if is_http_running():
            col.label(text=f"HTTP: http://{host}:{mcp.http_port}", icon='WORLD')
        if mcp.remote_access and mcp.local_ip:
            col.label(text=f"LAN IP: {mcp.local_ip}", icon='WORLD_DATA')

    # Server settings
    layout.separator()
    box = layout.box()
    box.label(text="Settings", icon='PREFERENCES')
    box.prop(mcp, "socket_port")
    box.prop(mcp, "http_port")
    box.prop(mcp, "remote_access")
    box.prop(mcp, "auto_start")
    box.prop(mcp, "allow_python_exec")

    # Start/Stop buttons
    row = box.row(align=True)
    row.scale_y = 1.4
    if is_server_running():
        row.operator("reca.mcp_stop", icon='PAUSE', text="Stop Server")
        row.operator("reca.mcp_test", icon='PLAY', text="Test")
    else:
        row.operator("reca.mcp_start", icon='PLAY', text="Start Server")

    # Agent config
    layout.separator()
    box = layout.box()
    box.label(text="AI Agent Setup", icon='GHOST_ENABLED')
    box.prop(mcp, "agent_type")

    # Show instructions based on agent
    col = box.column(align=True)
    agent = mcp.agent_type
    if agent == 'CLAUDE_DESKTOP':
        col.label(text="1. Install: pip install blender-mcp", icon='INFO')
        col.label(text="2. Copy config below to claude_desktop_config.json")
        col.label(text="3. Start server above, then open Claude Desktop")
    elif agent == 'CLAUDE_CODE':
        col.label(text="1. Start server above", icon='INFO')
        http_host = mcp.local_ip if mcp.remote_access and mcp.local_ip else "127.0.0.1"
        col.label(text=f"2. Run: claude mcp add reca http://{http_host}:{mcp.http_port}")
    elif agent == 'CURSOR':
        col.label(text="1. Install: pip install blender-mcp", icon='INFO')
        col.label(text="2. Cursor > Settings > MCP > Add Server")
        col.label(text="3. Paste config below")
    elif agent == 'OPENCLAW':
        col.label(text="1. Start server above", icon='INFO')
        col.label(text="2. Add HTTP endpoint in OpenClaw settings")
    else:
        col.label(text="1. Start server above", icon='INFO')
        http_host = mcp.local_ip if mcp.remote_access and mcp.local_ip else "127.0.0.1"
        col.label(text=f"2. Connect to http://{http_host}:{mcp.http_port}")

    box.operator("reca.mcp_generate_config", icon='COPYDOWN')

    # Available tools
    layout.separator()
    box = layout.box()
    box.label(text=f"Available Tools ({len(MCP_TOOLS)})", icon='TOOL_SETTINGS')
    col = box.column(align=True)
    for name, spec in MCP_TOOLS.items():
        row = col.row()
        row.label(text=name, icon='DOT')
        row.label(text=spec["description"][:45])


# ─────────────────────────────────────────────
#  Auto-start handler
# ─────────────────────────────────────────────

def _auto_start_handler(dummy):
    """Start MCP servers automatically if configured."""
    for scene in bpy.data.scenes:
        if hasattr(scene, 'reca_mcp') and scene.reca_mcp.auto_start:
            mcp = scene.reca_mcp
            results = start_servers(mcp.socket_port, mcp.http_port, remote=mcp.remote_access)
            mcp.enabled = True
            if 'local_ip' in results:
                mcp.local_ip = results['local_ip']
            bind = "0.0.0.0" if mcp.remote_access else "localhost"
            mcp.status = f"Socket {bind}:{mcp.socket_port} | HTTP {bind}:{mcp.http_port}"
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
    stop_servers()
    if _auto_start_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_auto_start_handler)
    del bpy.types.Scene.reca_mcp
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
