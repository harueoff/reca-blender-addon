# RECA MCP Tools — Full Parameter Reference

## Table of Contents
1. [scene_info](#scene_info)
2. [list_objects](#list_objects)
3. [get_object_info](#get_object_info)
4. [add_object](#add_object)
5. [delete_object](#delete_object)
6. [transform_object](#transform_object)
7. [set_material](#set_material)
8. [add_light](#add_light)
9. [add_camera](#add_camera)
10. [setup_scene](#setup_scene)
11. [render](#render)
12. [set_render_settings](#set_render_settings)
13. [import_model](#import_model)
14. [export_model](#export_model)
15. [generate_procedural](#generate_procedural)
16. [add_modifier](#add_modifier)
17. [keyframe](#keyframe)
18. [execute_python](#execute_python)

---

## scene_info

Get current scene statistics — object count, vertex count, render settings.

**Parameters:** None

**Returns:**
```json
{
  "scene_name": "Scene",
  "object_count": 5,
  "mesh_count": 3,
  "total_vertices": 1234,
  "total_faces": 456,
  "materials": 2,
  "render_engine": "CYCLES",
  "resolution": [1920, 1080],
  "frame_current": 1,
  "frame_range": [1, 250]
}
```

---

## list_objects

List all objects in scene with transform and mesh info.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| type_filter | string | No | Filter: MESH, LIGHT, CAMERA, EMPTY, CURVE, ARMATURE |

**Returns:** Array of objects with name, type, location, rotation, scale, visible, vertices, faces.

---

## get_object_info

Get detailed information about a specific object.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Exact object name |

**Returns:** name, type, location, rotation_euler, rotation_deg, scale, dimensions, visible, parent, children, vertices, edges, faces, materials, modifiers.

---

## add_object

Add a primitive mesh object to the scene.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| primitive | string | Yes | — | One of: cube, sphere, cylinder, plane, cone, torus, ico_sphere, monkey, empty |
| size | number | No | 1.0 | Size/radius of the object |
| location | array | No | [0,0,0] | [x, y, z] position |
| name | string | No | auto | Custom name for the object |

**Example:**
```json
{"primitive": "sphere", "size": 2.0, "location": [3, 0, 1], "name": "MySphere"}
```

---

## delete_object

Delete an object by name, or delete all selected objects.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | No | Object name. If omitted, deletes all selected objects. |

---

## transform_object

Set position, rotation, or scale of an object.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Object name |
| location | array | No | [x, y, z] world position |
| rotation | array | No | [rx, ry, rz] in **degrees** |
| scale | array | No | [sx, sy, sz] scale factors |

**Example:**
```json
{"name": "Cube", "location": [2, 0, 0], "rotation": [0, 0, 45], "scale": [1, 1, 2]}
```

---

## set_material

Apply a PBR material to a mesh object. Can use a preset or custom values.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| object_name | string | Yes | Target mesh object |
| preset | string | No | RECA preset name (see list below) |
| color | array | No | [r, g, b] base color, 0.0–1.0 |
| metallic | number | No | 0.0 (dielectric) to 1.0 (metal) |
| roughness | number | No | 0.0 (mirror) to 1.0 (rough) |
| emission_color | array | No | [r, g, b] emission color |
| emission_strength | number | No | Emission intensity |

**Presets:**
- Metals: METAL_GOLD, METAL_SILVER, METAL_COPPER, METAL_BRUSHED
- Glass: GLASS_CLEAR, GLASS_FROSTED, GLASS_COLORED
- Plastic: PLASTIC_GLOSSY, PLASTIC_MATTE
- Wood: WOOD_POLISHED, WOOD_ROUGH
- Stone: STONE_MARBLE, STONE_GRANITE
- Fabric: FABRIC_SILK, FABRIC_COTTON
- Special: SKIN (SSS), NEON (emission), HOLOGRAPHIC, CERAMIC, RUBBER

**Examples:**
```json
{"object_name": "Cube", "preset": "METAL_GOLD"}
{"object_name": "Sphere", "color": [0.8, 0.1, 0.1], "metallic": 0.0, "roughness": 0.3}
{"object_name": "Ring", "color": [1, 0.5, 0], "emission_color": [1, 0.5, 0], "emission_strength": 5.0}
```

---

## add_light

Add a light source to the scene.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | No | MCP_Light | Light name |
| type | string | No | AREA | AREA, POINT, SUN, SPOT |
| location | array | No | [0,0,5] | [x, y, z] |
| energy | number | No | 100 | Light power in watts |
| color | array | No | [1,1,1] | [r, g, b] |
| size | number | No | 1.0 | Light size (AREA/POINT) |

---

## add_camera

Add a camera and set it as the active scene camera.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | No | MCP_Camera | Camera name |
| location | array | No | [7,-6,5] | [x, y, z] |
| lens | number | No | 50 | Focal length in mm |
| look_at | array | No | — | [x, y, z] point to aim at |

**Example:**
```json
{"location": [5, -5, 3], "lens": 35, "look_at": [0, 0, 0]}
```

---

## setup_scene

Quick scene setup using RECA's built-in presets. Combines lighting, camera, and environment in one call.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| lighting | string | No | STUDIO_3POINT, STUDIO_SOFT, OUTDOOR_SUN, INDOOR_WARM, DRAMATIC, NEON, GOLDEN_HOUR, MOONLIGHT |
| camera | string | No | FRONT, THREE_QUARTER, TOP_DOWN, LOW_ANGLE, CLOSE_UP, WIDE |
| environment | string | No | INFINITE, GROUND, ROOM, PEDESTAL, GRADIENT |

**Example:**
```json
{"lighting": "STUDIO_3POINT", "camera": "THREE_QUARTER", "environment": "INFINITE"}
```

---

## render

Render the current scene to an image file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| filepath | string | No | Output file path. If omitted, renders to viewport. |
| samples | integer | No | Render samples (Cycles only) |
| engine | string | No | CYCLES or BLENDER_EEVEE_NEXT |
| resolution | array | No | [width, height] in pixels |

---

## set_render_settings

Configure render settings without rendering.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| engine | string | No | CYCLES or BLENDER_EEVEE_NEXT |
| samples | integer | No | Render samples |
| resolution | array | No | [width, height] |
| output_path | string | No | Default output directory |
| file_format | string | No | PNG, JPEG, EXR, OPEN_EXR, TIFF, BMP |

---

## import_model

Import a 3D model file into the scene.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| filepath | string | Yes | Absolute path to the file |
| format | string | No | Override format detection: obj, fbx, gltf, glb, stl |

**Returns:** List of imported object names and count.

---

## export_model

Export the scene or selected objects to a file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| filepath | string | Yes | Output file path |
| format | string | No | Override: obj, fbx, glb, gltf, stl, usd |
| selected_only | boolean | No | Export only selected objects (default: false) |

---

## generate_procedural

Generate complex procedural geometry using RECA's generators.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| generator | string | Yes | BUILDING, TERRAIN, TREE, ROCKS, CITY, ARRAY_PATTERN, SCATTER, PIPE |
| seed | integer | No | Random seed (default: 42). Same seed = same result. |

**Generators detail:**
- **BUILDING** — Multi-story building with windows
- **TERRAIN** — Landscape with noise-based height map
- **TREE** — Stylized tree with trunk and canopy
- **ROCKS** — Scattered rock formations
- **CITY** — Grid of buildings forming a cityscape
- **ARRAY_PATTERN** — Repeating pattern array
- **SCATTER** — Random scatter of objects on a surface
- **PIPE** — Connected pipe system with bends

---

## add_modifier

Add a modifier to an object.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| object_name | string | Yes | Target object |
| modifier_type | string | Yes | SUBSURF, MIRROR, ARRAY, BEVEL, SOLIDIFY, BOOLEAN, DECIMATE, REMESH, SMOOTH, WIREFRAME, etc. |

Additional modifier-specific parameters can be passed as extra keyword arguments.

---

## keyframe

Insert an animation keyframe on an object property.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| object_name | string | Yes | Object name |
| data_path | string | Yes | Property path: location, rotation_euler, scale, etc. |
| frame | integer | Yes | Frame number |
| value | any | No | Value to set before keyframing |

**Example — animate cube moving from left to right:**
```json
{"object_name": "Cube", "data_path": "location", "frame": 1, "value": [-3, 0, 0]}
{"object_name": "Cube", "data_path": "location", "frame": 60, "value": [3, 0, 0]}
```

---

## execute_python

Execute arbitrary Python code inside Blender's environment. Use only when no dedicated tool covers the operation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| code | string | Yes | Python code. `bpy` and `mathutils` are available. |

**Security note:** This tool may be disabled by the user in RECA settings. If it returns an error about being unavailable, inform the user they need to enable "Allow Python Execution" in RECA's MCP settings.

**Example:**
```json
{"code": "import bpy\nfor obj in bpy.data.objects:\n    if obj.type == 'MESH':\n        obj.display_type = 'WIRE'"}
```
