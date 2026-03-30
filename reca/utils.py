# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA shared utilities — common helpers used across all modules."""

import bpy
import os
import json
import time
from mathutils import Vector, Matrix


# ─────────────────────────────────────────────
#  Object helpers
# ─────────────────────────────────────────────

def tag_reca(obj, category="default"):
    """Tag an object as RECA-created with optional category."""
    obj["reca_tag"] = category
    obj["reca_timestamp"] = time.time()


def get_reca_objects(category=None):
    """Get all RECA-tagged objects, optionally filtered by category."""
    result = []
    for obj in bpy.data.objects:
        tag = obj.get("reca_tag")
        if tag is not None:
            if category is None or tag == category:
                result.append(obj)
    return result


def remove_reca_objects(category=None):
    """Remove all RECA-tagged objects."""
    for obj in get_reca_objects(category):
        bpy.data.objects.remove(obj, do_unlink=True)


def ensure_collection(name):
    """Get or create a collection by name, linked to the scene."""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link_to_collection(obj, collection):
    """Move object to a specific collection."""
    collection.objects.link(obj)
    for c in obj.users_collection:
        if c != collection:
            c.objects.unlink(obj)


def deselect_all():
    """Deselect all objects."""
    bpy.ops.object.select_all(action='DESELECT')


def select_only(obj):
    """Select only this object and make it active."""
    deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# ─────────────────────────────────────────────
#  Material helpers
# ─────────────────────────────────────────────

def make_principled_material(name, **kwargs):
    """Create a Principled BSDF material with given parameters.

    Supported kwargs: base_color, metallic, roughness, specular,
    transmission, emission_color, emission_strength, ior, alpha,
    subsurface, subsurface_color
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return mat

    param_map = {
        'base_color': ("Base Color", True),
        'metallic': ("Metallic", False),
        'roughness': ("Roughness", False),
        'specular': ("Specular IOR Level", False),
        'transmission': ("Transmission Weight", False),
        'emission_color': ("Emission Color", True),
        'emission_strength': ("Emission Strength", False),
        'ior': ("IOR", False),
        'alpha': ("Alpha", False),
        'subsurface': ("Subsurface Weight", False),
        'subsurface_color': ("Subsurface Radius", True),
    }

    for key, (input_name, is_color) in param_map.items():
        if key not in kwargs:
            continue
        val = kwargs[key]
        inp = bsdf.inputs.get(input_name)
        if inp is None:
            continue
        if is_color:
            inp.default_value = (*val, 1.0) if len(val) == 3 else val
        else:
            inp.default_value = val

    return mat


# ─────────────────────────────────────────────
#  Light helpers
# ─────────────────────────────────────────────

def add_light(name, light_type, location, rotation=(0, 0, 0),
              energy=100, color=(1, 1, 1), size=1.0):
    """Create a light and return the object."""
    bpy.ops.object.light_add(type=light_type, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.energy = energy
    obj.data.color = color
    if hasattr(obj.data, 'size'):
        obj.data.size = size
    elif hasattr(obj.data, 'shadow_soft_size'):
        obj.data.shadow_soft_size = size
    tag_reca(obj, "light")
    return obj


# ─────────────────────────────────────────────
#  Scene info
# ─────────────────────────────────────────────

def scene_stats():
    """Return a dict of scene statistics."""
    total_verts = sum(len(m.vertices) for m in bpy.data.meshes)
    total_faces = sum(len(m.polygons) for m in bpy.data.meshes)
    return {
        'objects': len(bpy.data.objects),
        'meshes': len(bpy.data.meshes),
        'materials': len(bpy.data.materials),
        'images': len(bpy.data.images),
        'collections': len(bpy.data.collections),
        'total_vertices': total_verts,
        'total_faces': total_faces,
        'objects_by_type': _count_by_type(),
    }


def _count_by_type():
    counts = {}
    for obj in bpy.data.objects:
        counts[obj.type] = counts.get(obj.type, 0) + 1
    return counts


# ─────────────────────────────────────────────
#  File / Preset helpers
# ─────────────────────────────────────────────

def reca_config_dir():
    """Get RECA config directory (create if needed)."""
    path = os.path.join(bpy.utils.user_resource('CONFIG'), "reca")
    os.makedirs(path, exist_ok=True)
    return path


def reca_presets_dir():
    """Get RECA presets directory."""
    path = os.path.join(reca_config_dir(), "presets")
    os.makedirs(path, exist_ok=True)
    return path


def save_json(filepath, data):
    """Save data as JSON."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(filepath, default=None):
    """Load JSON file, return default if not found."""
    if not os.path.isfile(filepath):
        return default
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ─────────────────────────────────────────────
#  Purge helpers
# ─────────────────────────────────────────────

PURGE_COLLECTIONS = (
    'meshes', 'materials', 'textures', 'images', 'node_groups',
    'worlds', 'cameras', 'lights', 'curves', 'fonts',
    'armatures', 'actions', 'particles',
)


def purge_orphans():
    """Remove all orphan data blocks. Returns count removed."""
    removed = 0
    for attr in PURGE_COLLECTIONS:
        data = getattr(bpy.data, attr, None)
        if data is None:
            continue
        for block in list(data):
            if block.users == 0:
                data.remove(block)
                removed += 1
    return removed
