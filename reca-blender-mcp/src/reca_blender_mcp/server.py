"""RECA Blender MCP Server.

Bridges MCP clients to RECA addon's TCP socket server running inside Blender.
Exposes 18 tools for controlling Blender: scene management, objects, materials,
lighting, cameras, rendering, procedural generation, animation, and code execution.
"""

import json
import os
import socket
import sys
from typing import Optional, List

from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────

BLENDER_HOST = os.environ.get("BLENDER_HOST", "localhost")
BLENDER_PORT = int(os.environ.get("BLENDER_PORT", "9876"))

mcp = FastMCP("reca_blender_mcp")


# ─────────────────────────────────────────────
#  Blender Socket Client
# ─────────────────────────────────────────────

def _send_command(command_type: str, params: dict | None = None) -> dict:
    """Send a JSON command to RECA addon's TCP socket and return the response.

    The RECA addon in Blender listens on a TCP socket and accepts JSON commands
    in the format: {"type": "command_name", "params": {...}}
    It responds with: {"status": "success|error", "result": ..., "message": ...}
    """
    payload = {"type": command_type}
    if params:
        payload["params"] = params

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60)
        sock.connect((BLENDER_HOST, BLENDER_PORT))
        sock.sendall(json.dumps(payload).encode("utf-8"))

        # Read response
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk.decode("utf-8", errors="replace"))
            # Check if we have a complete JSON response
            data = "".join(chunks)
            try:
                result = json.loads(data.strip())
                sock.close()
                return result
            except json.JSONDecodeError:
                continue

        sock.close()
        data = "".join(chunks).strip()
        if data:
            return json.loads(data)
        return {"status": "error", "message": "Empty response from Blender"}

    except ConnectionRefusedError:
        return {
            "status": "error",
            "message": (
                "Cannot connect to Blender. Make sure:\n"
                "1. Blender is running with RECA addon installed\n"
                "2. MCP server is started (RECA tab → MCP → Start Server)\n"
                f"3. Socket server is listening on {BLENDER_HOST}:{BLENDER_PORT}"
            ),
        }
    except socket.timeout:
        return {"status": "error", "message": "Connection to Blender timed out (60s). The operation may be too complex."}
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {e}"}


def _format_result(response: dict) -> str:
    """Format a Blender response into a string for MCP."""
    if response.get("status") == "error":
        msg = response.get("message", "Unknown error from Blender")
        return f"Error: {msg}"

    result = response.get("result", response)
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
#  Scene & Object Tools
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_get_scene_info",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_get_scene_info() -> str:
    """Get current Blender scene statistics: object count, vertices, faces, materials, render settings, frame range.

    Use this as a first step to understand the current state of the Blender scene before making changes.

    Returns:
        str: JSON with scene_name, object_count, mesh_count, total_vertices, total_faces,
             materials, render_engine, resolution, frame_current, frame_range.
    """
    return _format_result(_send_command("scene_info"))


@mcp.tool(
    name="blender_list_objects",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_list_objects(type_filter: Optional[str] = None) -> str:
    """List all objects in the Blender scene with their transforms and mesh info.

    Args:
        type_filter: Filter by object type — MESH, LIGHT, CAMERA, EMPTY, CURVE, ARMATURE.
                     If omitted, returns all objects.

    Returns:
        str: JSON array of objects with name, type, location, rotation, scale, visible,
             and (for meshes) vertices and faces count.
    """
    params = {}
    if type_filter:
        params["type_filter"] = type_filter
    return _format_result(_send_command("list_objects", params))


@mcp.tool(
    name="blender_get_object_info",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_get_object_info(name: str) -> str:
    """Get detailed information about a specific Blender object.

    Args:
        name: Exact object name (case-sensitive). Use blender_list_objects to find names.

    Returns:
        str: JSON with name, type, location, rotation, scale, dimensions, parent, children,
             vertices, edges, faces, materials list, and modifiers list.
    """
    return _format_result(_send_command("get_object_info", {"name": name}))


@mcp.tool(
    name="blender_add_object",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def blender_add_object(
    primitive: str,
    size: float = 1.0,
    location: Optional[List[float]] = None,
    name: Optional[str] = None,
) -> str:
    """Add a primitive 3D object to the Blender scene.

    Args:
        primitive: Object type — cube, sphere, cylinder, plane, cone, torus, ico_sphere, monkey, empty.
        size: Size/radius of the object (default: 1.0).
        location: [x, y, z] world position. Blender uses Z-up coordinate system.
        name: Custom name. If omitted, Blender auto-names (e.g., "Cube", "Cube.001").

    Returns:
        str: JSON with name, type, and location of the created object.
    """
    params = {"primitive": primitive, "size": size}
    if location:
        params["location"] = location
    if name:
        params["name"] = name
    return _format_result(_send_command("add_object", params))


@mcp.tool(
    name="blender_delete_object",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
)
async def blender_delete_object(name: Optional[str] = None) -> str:
    """Delete an object from the Blender scene.

    Args:
        name: Object name to delete. If omitted, deletes all currently selected objects.

    Returns:
        str: JSON confirming which object(s) were deleted.
    """
    params = {}
    if name:
        params["name"] = name
    return _format_result(_send_command("delete_object", params))


@mcp.tool(
    name="blender_transform_object",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_transform_object(
    name: str,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
) -> str:
    """Set the position, rotation, or scale of a Blender object.

    Args:
        name: Object name (case-sensitive).
        location: [x, y, z] world position.
        rotation: [rx, ry, rz] rotation in DEGREES (not radians).
        scale: [sx, sy, sz] scale factors (1.0 = original size).

    Returns:
        str: JSON with updated name, location, rotation_deg, and scale.
    """
    params = {"name": name}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale
    return _format_result(_send_command("transform_object", params))


# ─────────────────────────────────────────────
#  Material Tools
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_set_material",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_set_material(
    object_name: str,
    preset: Optional[str] = None,
    color: Optional[List[float]] = None,
    metallic: Optional[float] = None,
    roughness: Optional[float] = None,
    emission_color: Optional[List[float]] = None,
    emission_strength: Optional[float] = None,
) -> str:
    """Apply a PBR material to a mesh object. Use presets for quick realistic materials or set custom values.

    Args:
        object_name: Target mesh object name.
        preset: RECA material preset — METAL_GOLD, METAL_SILVER, METAL_COPPER, METAL_BRUSHED,
                GLASS_CLEAR, GLASS_FROSTED, GLASS_COLORED, PLASTIC_GLOSSY, PLASTIC_MATTE,
                WOOD_POLISHED, WOOD_ROUGH, STONE_MARBLE, STONE_GRANITE, FABRIC_SILK, FABRIC_COTTON,
                SKIN, NEON, HOLOGRAPHIC, CERAMIC, RUBBER.
        color: [r, g, b] base color (0.0–1.0 range). E.g., [1, 0, 0] = red.
        metallic: 0.0 (dielectric/plastic) to 1.0 (metal).
        roughness: 0.0 (mirror/glossy) to 1.0 (rough/matte).
        emission_color: [r, g, b] glow color for emissive materials.
        emission_strength: Emission intensity (0 = no glow, 5+ = bright glow).

    Returns:
        str: JSON with material name and object name.
    """
    params = {"object_name": object_name}
    if preset:
        params["preset"] = preset
    if color:
        params["color"] = color
    if metallic is not None:
        params["metallic"] = metallic
    if roughness is not None:
        params["roughness"] = roughness
    if emission_color:
        params["emission_color"] = emission_color
    if emission_strength is not None:
        params["emission_strength"] = emission_strength
    return _format_result(_send_command("set_material", params))


# ─────────────────────────────────────────────
#  Lighting & Camera
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_add_light",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def blender_add_light(
    name: str = "MCP_Light",
    type: str = "AREA",
    location: Optional[List[float]] = None,
    energy: float = 100,
    color: Optional[List[float]] = None,
    size: float = 1.0,
) -> str:
    """Add a light source to the Blender scene.

    Args:
        name: Light name (default: "MCP_Light").
        type: Light type — AREA (soft shadows), POINT (omnidirectional), SUN (directional), SPOT (cone).
        location: [x, y, z] position (default: [0, 0, 5]).
        energy: Light power in watts (default: 100). Use 1000+ for bright scenes.
        color: [r, g, b] light color (default: [1, 1, 1] white).
        size: Light source size — larger = softer shadows (default: 1.0).

    Returns:
        str: JSON with light name, type, and energy.
    """
    params = {"name": name, "type": type, "energy": energy, "size": size}
    if location:
        params["location"] = location
    if color:
        params["color"] = color
    return _format_result(_send_command("add_light", params))


@mcp.tool(
    name="blender_add_camera",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def blender_add_camera(
    name: str = "MCP_Camera",
    location: Optional[List[float]] = None,
    lens: float = 50,
    look_at: Optional[List[float]] = None,
) -> str:
    """Add a camera to the scene and set it as the active render camera.

    Args:
        name: Camera name (default: "MCP_Camera").
        location: [x, y, z] camera position (default: [7, -6, 5]).
        lens: Focal length in mm. 35=wide, 50=normal, 85=portrait, 135=telephoto.
        look_at: [x, y, z] point the camera aims at. If omitted, camera points forward.

    Returns:
        str: JSON with camera name, lens, and location.
    """
    params = {"name": name, "lens": lens}
    if location:
        params["location"] = location
    if look_at:
        params["look_at"] = look_at
    return _format_result(_send_command("add_camera", params))


@mcp.tool(
    name="blender_setup_scene",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_setup_scene(
    lighting: Optional[str] = None,
    camera: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Quick professional scene setup using RECA presets. Combines lighting, camera, and environment.

    Args:
        lighting: STUDIO_3POINT (product), STUDIO_SOFT (portrait), OUTDOOR_SUN, INDOOR_WARM,
                  DRAMATIC, NEON, GOLDEN_HOUR, MOONLIGHT.
        camera: FRONT, THREE_QUARTER (most common), TOP_DOWN, LOW_ANGLE, CLOSE_UP, WIDE.
        environment: INFINITE (seamless backdrop), GROUND (flat plane), ROOM (enclosed),
                     PEDESTAL (product display), GRADIENT (color background).

    Returns:
        str: JSON confirming which presets were applied.
    """
    params = {}
    if lighting:
        params["lighting"] = lighting
    if camera:
        params["camera"] = camera
    if environment:
        params["environment"] = environment
    return _format_result(_send_command("setup_scene", params))


# ─────────────────────────────────────────────
#  Rendering
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_render",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def blender_render(
    filepath: Optional[str] = None,
    samples: Optional[int] = None,
    engine: Optional[str] = None,
    resolution: Optional[List[int]] = None,
) -> str:
    """Render the current Blender scene to an image file.

    Args:
        filepath: Output file path (e.g., "/tmp/render.png"). If omitted, renders to viewport.
        samples: Render quality — more samples = less noise (Cycles only). 32=fast, 128=good, 512=high.
        engine: CYCLES (ray-tracing, realistic) or BLENDER_EEVEE_NEXT (real-time, fast).
        resolution: [width, height] in pixels (e.g., [1920, 1080]).

    Returns:
        str: JSON confirming the render output path.
    """
    params = {}
    if filepath:
        params["filepath"] = filepath
    if samples:
        params["samples"] = samples
    if engine:
        params["engine"] = engine
    if resolution:
        params["resolution"] = resolution
    return _format_result(_send_command("render", params))


@mcp.tool(
    name="blender_set_render_settings",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_set_render_settings(
    engine: Optional[str] = None,
    samples: Optional[int] = None,
    resolution: Optional[List[int]] = None,
    output_path: Optional[str] = None,
    file_format: Optional[str] = None,
) -> str:
    """Configure render settings without actually rendering.

    Args:
        engine: CYCLES or BLENDER_EEVEE_NEXT.
        samples: Render samples (quality vs speed tradeoff).
        resolution: [width, height] in pixels.
        output_path: Default output directory for renders.
        file_format: PNG, JPEG, EXR, OPEN_EXR, TIFF, BMP.

    Returns:
        str: JSON with current engine and resolution after changes.
    """
    params = {}
    if engine:
        params["engine"] = engine
    if samples:
        params["samples"] = samples
    if resolution:
        params["resolution"] = resolution
    if output_path:
        params["output_path"] = output_path
    if file_format:
        params["file_format"] = file_format
    return _format_result(_send_command("set_render_settings", params))


# ─────────────────────────────────────────────
#  Import/Export
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_import_model",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def blender_import_model(filepath: str, format: Optional[str] = None) -> str:
    """Import a 3D model file into Blender.

    Args:
        filepath: Absolute path to the model file.
        format: Override format detection — obj, fbx, gltf, glb, stl.

    Returns:
        str: JSON with list of imported object names and count.
    """
    params = {"filepath": filepath}
    if format:
        params["format"] = format
    return _format_result(_send_command("import_model", params))


@mcp.tool(
    name="blender_export_model",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def blender_export_model(
    filepath: str,
    format: Optional[str] = None,
    selected_only: bool = False,
) -> str:
    """Export the Blender scene or selected objects to a 3D file.

    Args:
        filepath: Output file path with extension (e.g., "/tmp/model.glb").
        format: Override — obj, fbx, glb, gltf, stl, usd.
        selected_only: If true, export only selected objects (default: false = entire scene).

    Returns:
        str: JSON confirming the export path.
    """
    params = {"filepath": filepath, "selected_only": selected_only}
    if format:
        params["format"] = format
    return _format_result(_send_command("export_model", params))


# ─────────────────────────────────────────────
#  Procedural Generation
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_generate_procedural",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_generate_procedural(generator: str, seed: int = 42) -> str:
    """Generate complex procedural 3D geometry using RECA's built-in generators.

    Args:
        generator: BUILDING (multi-story), TERRAIN (landscape), TREE (stylized),
                   ROCKS (formations), CITY (cityscape), ARRAY_PATTERN (repeating),
                   SCATTER (random placement), PIPE (connected pipes).
        seed: Random seed — same seed produces identical results (default: 42).

    Returns:
        str: JSON confirming the generator type and seed used.
    """
    return _format_result(_send_command("generate_procedural", {"generator": generator, "seed": seed}))


# ─────────────────────────────────────────────
#  Modifiers & Animation
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_add_modifier",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def blender_add_modifier(object_name: str, modifier_type: str) -> str:
    """Add a modifier to a Blender object.

    Args:
        object_name: Target object name.
        modifier_type: SUBSURF (smooth), MIRROR, ARRAY (repeat), BEVEL (rounded edges),
                       SOLIDIFY (thickness), BOOLEAN, DECIMATE (reduce poly), REMESH, WIREFRAME.

    Returns:
        str: JSON with modifier name, type, and target object.
    """
    return _format_result(_send_command("add_modifier", {"object_name": object_name, "modifier_type": modifier_type}))


@mcp.tool(
    name="blender_keyframe",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def blender_keyframe(
    object_name: str,
    data_path: str,
    frame: int,
    value: Optional[object] = None,
) -> str:
    """Insert an animation keyframe on an object property.

    Args:
        object_name: Object to animate.
        data_path: Property to keyframe — "location", "rotation_euler", "scale",
                   or nested paths like "data.energy" (for lights).
        frame: Frame number to insert the keyframe at.
        value: Value to set before keyframing (e.g., [0, 0, 2] for location).
               If omitted, keyframes the current value.

    Returns:
        str: JSON confirming object, data_path, and frame.
    """
    params = {"object_name": object_name, "data_path": data_path, "frame": frame}
    if value is not None:
        params["value"] = value
    return _format_result(_send_command("keyframe", params))


# ─────────────────────────────────────────────
#  Code Execution
# ─────────────────────────────────────────────

@mcp.tool(
    name="blender_execute_python",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
)
async def blender_execute_python(code: str) -> str:
    """Execute arbitrary Python code inside Blender's environment.

    Use this as a last resort when no dedicated tool covers the operation.
    The code runs with `bpy` and `mathutils` available in scope.

    Note: This tool may be disabled by the user in RECA's MCP settings
    ("Allow Python Execution" must be checked).

    Args:
        code: Python code to execute. Use `bpy` for Blender API, `mathutils` for vectors/matrices.

    Returns:
        str: JSON with stdout output and success status, or error details.
    """
    return _format_result(_send_command("execute_python", {"code": code}))


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────

def main():
    """Run the RECA Blender MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
