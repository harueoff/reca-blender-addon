# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA Material Tools — material creation, library, and utilities."""

import bpy
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    FloatProperty,
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    PointerProperty,
    IntProperty,
)
from ..utils import make_principled_material


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_material_tools(PropertyGroup):
    # Material presets
    mat_preset: EnumProperty(
        name="Material Preset",
        items=[
            ('METAL_GOLD', "Gold Metal", "Polished gold"),
            ('METAL_SILVER', "Silver Metal", "Polished silver"),
            ('METAL_COPPER', "Copper Metal", "Copper"),
            ('METAL_IRON', "Iron / Steel", "Brushed steel"),
            ('GLASS_CLEAR', "Clear Glass", "Transparent glass"),
            ('GLASS_FROSTED', "Frosted Glass", "Frosted translucent"),
            ('GLASS_COLORED', "Colored Glass", "Tinted glass"),
            ('PLASTIC_GLOSSY', "Glossy Plastic", "Shiny plastic"),
            ('PLASTIC_MATTE', "Matte Plastic", "Matte plastic"),
            ('RUBBER', "Rubber", "Soft rubber"),
            ('WOOD_LIGHT', "Light Wood", "Light wood grain"),
            ('WOOD_DARK', "Dark Wood", "Dark wood grain"),
            ('CONCRETE', "Concrete", "Rough concrete"),
            ('MARBLE', "Marble", "Polished marble"),
            ('FABRIC', "Fabric", "Cloth / fabric"),
            ('SKIN', "Skin (SSS)", "Subsurface skin"),
            ('CERAMIC', "Ceramic", "Glazed ceramic"),
            ('EMISSION', "Emission", "Glowing emissive"),
            ('NEON', "Neon Glow", "Bright neon emission"),
            ('HOLOGRAPHIC', "Holographic", "Iridescent holographic"),
        ],
        default='METAL_GOLD',
    )

    # Custom material params
    base_color: FloatVectorProperty(
        name="Base Color",
        subtype='COLOR',
        default=(0.8, 0.8, 0.8),
        min=0.0, max=1.0,
    )
    metallic: FloatProperty(name="Metallic", default=0.0, min=0.0, max=1.0)
    roughness: FloatProperty(name="Roughness", default=0.5, min=0.0, max=1.0)
    specular: FloatProperty(name="Specular", default=0.5, min=0.0, max=1.0)
    transmission: FloatProperty(name="Transmission", default=0.0, min=0.0, max=1.0)
    emission_strength: FloatProperty(name="Emission Strength", default=0.0, min=0.0, max=100.0)
    emission_color: FloatVectorProperty(
        name="Emission Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0, max=1.0,
    )
    ior: FloatProperty(name="IOR", default=1.45, min=1.0, max=3.0)
    alpha: FloatProperty(name="Alpha", default=1.0, min=0.0, max=1.0)
    subsurface: FloatProperty(name="Subsurface", default=0.0, min=0.0, max=1.0)
    subsurface_color: FloatVectorProperty(
        name="Subsurface Color",
        subtype='COLOR',
        default=(0.8, 0.2, 0.1),
        min=0.0, max=1.0,
    )

    # Texture
    use_noise_texture: BoolProperty(name="Add Noise Texture", default=False)
    noise_scale: FloatProperty(name="Noise Scale", default=5.0, min=0.1, max=100.0)
    noise_strength: FloatProperty(name="Noise Strength", default=0.5, min=0.0, max=2.0)

    # Material name
    mat_name: StringProperty(name="Name", default="RECA_Material")

    # Utility
    assign_mode: EnumProperty(
        name="Assign To",
        items=[
            ('SELECTED', "Selected Objects", ""),
            ('ALL_MESH', "All Meshes", ""),
            ('ACTIVE', "Active Object", ""),
        ],
        default='SELECTED',
    )

    # Random materials
    rand_hue_range: FloatProperty(name="Hue Range", default=1.0, min=0.0, max=1.0)
    rand_saturation: FloatProperty(name="Saturation", default=0.7, min=0.0, max=1.0)
    rand_value: FloatProperty(name="Value", default=0.8, min=0.0, max=1.0)
    rand_seed: IntProperty(name="Seed", default=42, min=0)


# ─────────────────────────────────────────────
#  Material creation helpers
# ─────────────────────────────────────────────

def _create_principled_material(name, **kwargs):
    """Thin wrapper around utils.make_principled_material with blend_mode support."""
    blend = kwargs.pop('blend_mode', None)
    mat = make_principled_material(name, **kwargs)
    if blend == 'ALPHA':
        mat.blend_method = 'HASHED'
    return mat


PRESET_PARAMS = {
    'METAL_GOLD': dict(base_color=(1.0, 0.76, 0.33), metallic=1.0, roughness=0.2, specular=0.8),
    'METAL_SILVER': dict(base_color=(0.9, 0.9, 0.92), metallic=1.0, roughness=0.15, specular=0.9),
    'METAL_COPPER': dict(base_color=(0.72, 0.45, 0.2), metallic=1.0, roughness=0.25, specular=0.7),
    'METAL_IRON': dict(base_color=(0.55, 0.55, 0.58), metallic=1.0, roughness=0.4, specular=0.6),
    'GLASS_CLEAR': dict(base_color=(0.95, 0.95, 0.95), metallic=0.0, roughness=0.0, transmission=1.0, ior=1.5),
    'GLASS_FROSTED': dict(base_color=(0.9, 0.92, 0.95), metallic=0.0, roughness=0.3, transmission=0.9, ior=1.5),
    'GLASS_COLORED': dict(base_color=(0.2, 0.5, 0.8), metallic=0.0, roughness=0.05, transmission=0.85, ior=1.5),
    'PLASTIC_GLOSSY': dict(base_color=(0.8, 0.1, 0.1), metallic=0.0, roughness=0.1, specular=0.6),
    'PLASTIC_MATTE': dict(base_color=(0.3, 0.5, 0.7), metallic=0.0, roughness=0.7, specular=0.3),
    'RUBBER': dict(base_color=(0.15, 0.15, 0.15), metallic=0.0, roughness=0.9, specular=0.1),
    'WOOD_LIGHT': dict(base_color=(0.6, 0.4, 0.2), metallic=0.0, roughness=0.65, specular=0.2),
    'WOOD_DARK': dict(base_color=(0.25, 0.13, 0.06), metallic=0.0, roughness=0.7, specular=0.2),
    'CONCRETE': dict(base_color=(0.5, 0.48, 0.45), metallic=0.0, roughness=0.95, specular=0.1),
    'MARBLE': dict(base_color=(0.92, 0.9, 0.88), metallic=0.0, roughness=0.15, specular=0.5),
    'FABRIC': dict(base_color=(0.4, 0.2, 0.3), metallic=0.0, roughness=0.95, specular=0.05),
    'SKIN': dict(base_color=(0.8, 0.55, 0.4), metallic=0.0, roughness=0.5, subsurface=0.3,
                 subsurface_color=(0.9, 0.3, 0.15)),
    'CERAMIC': dict(base_color=(0.9, 0.88, 0.85), metallic=0.0, roughness=0.1, specular=0.7),
    'EMISSION': dict(base_color=(0.0, 0.0, 0.0), emission_color=(1.0, 0.8, 0.4), emission_strength=10.0),
    'NEON': dict(base_color=(0.0, 0.0, 0.0), emission_color=(0.0, 1.0, 0.8), emission_strength=30.0),
    'HOLOGRAPHIC': dict(base_color=(0.7, 0.7, 0.9), metallic=0.8, roughness=0.1, specular=1.0),
}


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_create_preset_material(Operator):
    """Create material from preset and assign to objects"""
    bl_idname = "reca.create_preset_material"
    bl_label = "Create Preset Material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mt = context.scene.reca_material_tools
        preset = mt.mat_preset
        params = PRESET_PARAMS.get(preset, {})
        mat = _create_principled_material(f"RECA_{preset}", **params)
        self._assign(context, mt, mat)
        self.report({'INFO'}, f"Created: {preset}")
        return {'FINISHED'}

    def _assign(self, context, mt, mat):
        if mt.assign_mode == 'ACTIVE':
            obj = context.active_object
            if obj and obj.type == 'MESH':
                obj.data.materials.clear()
                obj.data.materials.append(mat)
        elif mt.assign_mode == 'SELECTED':
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    obj.data.materials.clear()
                    obj.data.materials.append(mat)
        elif mt.assign_mode == 'ALL_MESH':
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    obj.data.materials.clear()
                    obj.data.materials.append(mat)


class RECA_OT_create_custom_material(Operator):
    """Create material from custom parameters"""
    bl_idname = "reca.create_custom_material"
    bl_label = "Create Custom Material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mt = context.scene.reca_material_tools
        params = {
            'base_color': tuple(mt.base_color),
            'metallic': mt.metallic,
            'roughness': mt.roughness,
            'specular': mt.specular,
            'transmission': mt.transmission,
            'emission_strength': mt.emission_strength,
            'emission_color': tuple(mt.emission_color),
            'ior': mt.ior,
            'alpha': mt.alpha,
            'subsurface': mt.subsurface,
            'subsurface_color': tuple(mt.subsurface_color),
        }
        mat = _create_principled_material(mt.mat_name, **params)

        # Noise texture
        if mt.use_noise_texture:
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            bsdf = nodes.get("Principled BSDF")
            tex_coord = nodes.new('ShaderNodeTexCoord')
            noise = nodes.new('ShaderNodeTexNoise')
            noise.inputs['Scale'].default_value = mt.noise_scale
            color_mix = nodes.new('ShaderNodeMix')
            color_mix.data_type = 'RGBA'
            color_mix.inputs['Factor'].default_value = mt.noise_strength
            color_mix.inputs[6].default_value = (*mt.base_color, 1.0)
            links.new(tex_coord.outputs['Object'], noise.inputs['Vector'])
            links.new(noise.outputs['Color'], color_mix.inputs[7])
            if bsdf:
                links.new(color_mix.outputs[2], bsdf.inputs['Base Color'])

        # Assign
        if mt.assign_mode == 'ACTIVE' and context.active_object:
            obj = context.active_object
            if obj.type == 'MESH':
                obj.data.materials.clear()
                obj.data.materials.append(mat)
        elif mt.assign_mode == 'SELECTED':
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    obj.data.materials.clear()
                    obj.data.materials.append(mat)

        self.report({'INFO'}, f"Created: {mt.mat_name}")
        return {'FINISHED'}


class RECA_OT_random_materials(Operator):
    """Assign random colored materials to selected objects"""
    bl_idname = "reca.random_materials"
    bl_label = "Random Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import random
        import colorsys
        mt = context.scene.reca_material_tools
        random.seed(mt.rand_seed)

        targets = context.selected_objects
        for i, obj in enumerate(targets):
            if obj.type != 'MESH':
                continue
            hue = random.uniform(0, mt.rand_hue_range)
            r, g, b = colorsys.hsv_to_rgb(hue, mt.rand_saturation, mt.rand_value)
            mat = _create_principled_material(
                f"RECA_Random_{i:03d}",
                base_color=(r, g, b),
                roughness=random.uniform(0.3, 0.8),
                metallic=random.uniform(0.0, 0.3),
            )
            obj.data.materials.clear()
            obj.data.materials.append(mat)

        self.report({'INFO'}, f"Assigned random materials to {len(targets)} objects")
        return {'FINISHED'}


class RECA_OT_remove_unused_materials(Operator):
    """Remove all unused material slots from selected objects"""
    bl_idname = "reca.remove_unused_materials"
    bl_label = "Remove Unused Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            # Remove empty material slots
            for i in range(len(obj.material_slots) - 1, -1, -1):
                if obj.material_slots[i].material is None:
                    obj.active_material_index = i
                    bpy.ops.object.material_slot_remove({'object': obj})
                    count += 1
        self.report({'INFO'}, f"Removed {count} empty material slots")
        return {'FINISHED'}


class RECA_OT_material_to_vertex_color(Operator):
    """Bake material base colors to vertex colors"""
    bl_idname = "reca.mat_to_vertex_color"
    bl_label = "Materials to Vertex Colors"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data

        if not mesh.color_attributes:
            mesh.color_attributes.new(name="RECA_MatColor", type='BYTE_COLOR', domain='CORNER')
        color_layer = mesh.color_attributes.active_color

        if color_layer is None:
            self.report({'ERROR'}, "Could not create color attribute")
            return {'CANCELLED'}

        for poly in mesh.polygons:
            mat_idx = poly.material_index
            color = (0.8, 0.8, 0.8, 1.0)
            if mat_idx < len(obj.material_slots):
                mat = obj.material_slots[mat_idx].material
                if mat and mat.use_nodes:
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        color = bsdf.inputs["Base Color"].default_value

            for loop_idx in poly.loop_indices:
                color_layer.data[loop_idx].color = color

        self.report({'INFO'}, "Baked material colors to vertex colors")
        return {'FINISHED'}


class RECA_OT_replace_material(Operator):
    """Replace a material across all objects"""
    bl_idname = "reca.replace_material"
    bl_label = "Replace Material"
    bl_options = {'REGISTER', 'UNDO'}

    source_mat: StringProperty(name="Source Material")
    target_mat: StringProperty(name="Target Material")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        source = bpy.data.materials.get(self.source_mat)
        target = bpy.data.materials.get(self.target_mat)
        if not source or not target:
            self.report({'ERROR'}, "Material not found")
            return {'CANCELLED'}

        count = 0
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for i, slot in enumerate(obj.material_slots):
                if slot.material == source:
                    slot.material = target
                    count += 1

        self.report({'INFO'}, f"Replaced {count} slots")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    mt = context.scene.reca_material_tools

    # Preset materials
    box = layout.box()
    box.label(text="Material Presets", icon='MATERIAL')
    box.prop(mt, "mat_preset", text="")
    box.prop(mt, "assign_mode")
    box.operator("reca.create_preset_material", icon='ADD')

    # Custom material
    box = layout.box()
    box.label(text="Custom Material", icon='NODE_MATERIAL')
    box.prop(mt, "mat_name")
    box.prop(mt, "base_color")
    row = box.row(align=True)
    row.prop(mt, "metallic", slider=True)
    row.prop(mt, "roughness", slider=True)
    row = box.row(align=True)
    row.prop(mt, "specular", slider=True)
    row.prop(mt, "transmission", slider=True)

    col = box.column()
    col.prop(mt, "emission_color")
    col.prop(mt, "emission_strength")
    col.prop(mt, "ior")
    col.prop(mt, "alpha", slider=True)

    col = box.column()
    col.prop(mt, "subsurface", slider=True)
    if mt.subsurface > 0:
        col.prop(mt, "subsurface_color")

    box.prop(mt, "use_noise_texture")
    if mt.use_noise_texture:
        box.prop(mt, "noise_scale")
        box.prop(mt, "noise_strength", slider=True)

    box.operator("reca.create_custom_material", icon='ADD')

    # Random
    box = layout.box()
    box.label(text="Random Materials", icon='COLOR')
    box.prop(mt, "rand_seed")
    box.prop(mt, "rand_hue_range", slider=True)
    box.prop(mt, "rand_saturation", slider=True)
    box.prop(mt, "rand_value", slider=True)
    box.operator("reca.random_materials", icon='FORCE_TURBULENCE')

    # Utilities
    box = layout.box()
    box.label(text="Utilities", icon='TOOL_SETTINGS')
    box.operator("reca.remove_unused_materials", icon='TRASH')
    box.operator("reca.mat_to_vertex_color", icon='VPAINT_HLT')
    box.operator("reca.replace_material", icon='UV_SYNC_SELECT')


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_material_tools,
    RECA_OT_create_preset_material,
    RECA_OT_create_custom_material,
    RECA_OT_random_materials,
    RECA_OT_remove_unused_materials,
    RECA_OT_material_to_vertex_color,
    RECA_OT_replace_material,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_material_tools = PointerProperty(type=RECA_PG_material_tools)


def unregister():
    del bpy.types.Scene.reca_material_tools
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
