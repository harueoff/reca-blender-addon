# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA Scene Builder — one-click professional scene setups."""

import bpy
import math
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    BoolProperty,
    IntProperty,
    StringProperty,
    PointerProperty,
)
from ..utils import make_principled_material, add_light, tag_reca, ensure_collection


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_scene_builder(PropertyGroup):
    # Lighting preset
    lighting_preset: EnumProperty(
        name="Lighting",
        items=[
            ('STUDIO_3POINT', "Studio 3-Point", "Classic 3-point studio lighting"),
            ('STUDIO_SOFT', "Studio Soft", "Soft diffused studio lighting"),
            ('HDRI_OUTDOOR', "Outdoor HDRI", "Outdoor environment lighting"),
            ('DRAMATIC', "Dramatic", "High contrast dramatic lighting"),
            ('PRODUCT', "Product Shot", "Clean product photography lighting"),
            ('SUNSET', "Sunset", "Warm sunset lighting"),
            ('NEON', "Neon / Cyberpunk", "Colorful neon accent lighting"),
            ('FLAT', "Flat / UI", "Even flat lighting for icons and UI renders"),
        ],
        default='STUDIO_3POINT',
    )

    # Camera preset
    camera_preset: EnumProperty(
        name="Camera",
        items=[
            ('PERSPECTIVE', "Perspective", "Standard perspective camera"),
            ('ORTHO', "Orthographic", "Orthographic camera"),
            ('PORTRAIT', "Portrait", "Portrait focal length (85mm)"),
            ('WIDE', "Wide Angle", "Wide angle (24mm)"),
            ('MACRO', "Macro", "Macro close-up (100mm)"),
            ('CINEMATIC', "Cinematic", "Anamorphic style (50mm 2.39:1)"),
        ],
        default='PERSPECTIVE',
    )

    # Environment
    env_preset: EnumProperty(
        name="Environment",
        items=[
            ('NONE', "None", "No environment"),
            ('INFINITE_FLOOR', "Infinite Floor", "Seamless infinite floor"),
            ('CYCLORAMA', "Cyclorama", "Studio cyclorama wall"),
            ('GRADIENT_BG', "Gradient BG", "Gradient background"),
            ('TURNTABLE', "Turntable", "Circular turntable base"),
        ],
        default='NONE',
    )

    env_color: FloatVectorProperty(
        name="Environment Color",
        subtype='COLOR',
        default=(0.8, 0.8, 0.8),
        min=0.0,
        max=1.0,
    )
    env_color_2: FloatVectorProperty(
        name="Gradient Color 2",
        subtype='COLOR',
        default=(0.1, 0.1, 0.15),
        min=0.0,
        max=1.0,
    )

    floor_size: FloatProperty(name="Floor Size", default=20.0, min=1.0, max=200.0)
    floor_glossy: FloatProperty(name="Floor Glossiness", default=0.0, min=0.0, max=1.0)

    # Quick setup
    clear_scene_first: BoolProperty(name="Clear Scene First", default=True)
    add_lights: BoolProperty(name="Add Lights", default=True)
    add_camera: BoolProperty(name="Add Camera", default=True)
    add_environment: BoolProperty(name="Add Environment", default=True)

    # Resolution
    res_x: IntProperty(name="Resolution X", default=1920, min=1, max=16384)
    res_y: IntProperty(name="Resolution Y", default=1080, min=1, max=16384)


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_clear_scene(Operator):
    """Remove all objects, orphan data, and reset scene"""
    bl_idname = "reca.clear_scene"
    bl_label = "Clear Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Delete all objects
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

        # Purge orphan data
        for attr in ('meshes', 'materials', 'textures', 'images',
                      'cameras', 'lights', 'curves', 'armatures'):
            data = getattr(bpy.data, attr, None)
            if data is None:
                continue
            for block in list(data):
                if block.users == 0:
                    data.remove(block)

        self.report({'INFO'}, "Scene cleared")
        return {'FINISHED'}


class RECA_OT_setup_lighting(Operator):
    """Set up professional lighting based on selected preset"""
    bl_idname = "reca.setup_lighting"
    bl_label = "Setup Lighting"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sb = context.scene.reca_scene_builder
        preset = sb.lighting_preset

        # Remove existing RECA lights
        for obj in list(bpy.data.objects):
            if obj.name.startswith("RECA_Light"):
                bpy.data.objects.remove(obj, do_unlink=True)

        if preset == 'STUDIO_3POINT':
            self._three_point(context)
        elif preset == 'STUDIO_SOFT':
            self._soft_studio(context)
        elif preset == 'DRAMATIC':
            self._dramatic(context)
        elif preset == 'PRODUCT':
            self._product(context)
        elif preset == 'SUNSET':
            self._sunset(context)
        elif preset == 'NEON':
            self._neon(context)
        elif preset == 'FLAT':
            self._flat(context)
        elif preset == 'HDRI_OUTDOOR':
            self._hdri_outdoor(context)

        self.report({'INFO'}, f"Lighting: {preset}")
        return {'FINISHED'}

    def _add_area_light(self, name, location, rotation, energy, size, color=(1, 1, 1)):
        bpy.ops.object.light_add(type='AREA', location=location, rotation=rotation)
        light = bpy.context.active_object
        light.name = name
        light.data.energy = energy
        light.data.size = size
        light.data.color = color
        return light

    def _add_point_light(self, name, location, energy, radius=0.25, color=(1, 1, 1)):
        bpy.ops.object.light_add(type='POINT', location=location)
        light = bpy.context.active_object
        light.name = name
        light.data.energy = energy
        light.data.shadow_soft_size = radius
        light.data.color = color
        return light

    def _three_point(self, context):
        self._add_area_light("RECA_Light_Key", (4, -3, 5),
                             (math.radians(50), 0, math.radians(30)), 500, 2)
        self._add_area_light("RECA_Light_Fill", (-3, -2, 3),
                             (math.radians(40), 0, math.radians(-40)), 150, 3)
        self._add_area_light("RECA_Light_Rim", (-1, 4, 4),
                             (math.radians(-40), 0, math.radians(180)), 300, 1.5)

    def _soft_studio(self, context):
        self._add_area_light("RECA_Light_Top", (0, 0, 6),
                             (0, 0, 0), 400, 5)
        self._add_area_light("RECA_Light_Front", (0, -4, 2),
                             (math.radians(70), 0, 0), 200, 4)
        self._add_area_light("RECA_Light_Back", (0, 4, 3),
                             (math.radians(-60), 0, 0), 100, 3)

    def _dramatic(self, context):
        self._add_area_light("RECA_Light_Key", (5, -2, 4),
                             (math.radians(55), 0, math.radians(40)), 800, 1)
        self._add_point_light("RECA_Light_Accent", (-3, 1, 0.5), 50,
                              color=(0.3, 0.5, 1.0))

    def _product(self, context):
        self._add_area_light("RECA_Light_Top", (0, 0, 5),
                             (0, 0, 0), 300, 4)
        self._add_area_light("RECA_Light_Left", (-4, -1, 2),
                             (math.radians(50), 0, math.radians(-60)), 200, 3)
        self._add_area_light("RECA_Light_Right", (4, -1, 2),
                             (math.radians(50), 0, math.radians(60)), 200, 3)
        self._add_area_light("RECA_Light_Back", (0, 3, 1),
                             (math.radians(-70), 0, 0), 150, 2)

    def _sunset(self, context):
        self._add_area_light("RECA_Light_Sun", (8, -3, 2),
                             (math.radians(70), 0, math.radians(20)), 600, 1.5,
                             color=(1.0, 0.55, 0.2))
        self._add_area_light("RECA_Light_Sky", (0, 0, 6),
                             (0, 0, 0), 100, 6,
                             color=(0.5, 0.6, 0.9))

    def _neon(self, context):
        self._add_area_light("RECA_Light_Pink", (3, -2, 2),
                             (math.radians(50), 0, math.radians(30)), 400, 2,
                             color=(1.0, 0.1, 0.5))
        self._add_area_light("RECA_Light_Cyan", (-3, -2, 2),
                             (math.radians(50), 0, math.radians(-30)), 400, 2,
                             color=(0.0, 0.8, 1.0))
        self._add_point_light("RECA_Light_Purple", (0, 2, 1), 100,
                              color=(0.5, 0.0, 1.0))

    def _flat(self, context):
        self._add_area_light("RECA_Light_Top", (0, 0, 6),
                             (0, 0, 0), 500, 8)
        self._add_area_light("RECA_Light_Front", (0, -5, 3),
                             (math.radians(60), 0, 0), 300, 6)

    def _hdri_outdoor(self, context):
        bpy.ops.object.light_add(type='SUN', location=(0, 0, 10),
                                 rotation=(math.radians(50), 0, math.radians(30)))
        sun = bpy.context.active_object
        sun.name = "RECA_Light_Sun"
        sun.data.energy = 5
        sun.data.color = (1.0, 0.95, 0.85)
        # Set world sky
        world = bpy.context.scene.world
        if world is None:
            world = bpy.data.worlds.new("RECA_World")
            bpy.context.scene.world = world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        nodes.clear()
        bg = nodes.new('ShaderNodeBackground')
        bg.inputs[0].default_value = (0.4, 0.6, 0.9, 1.0)
        bg.inputs[1].default_value = 1.0
        output = nodes.new('ShaderNodeOutputWorld')
        world.node_tree.links.new(bg.outputs[0], output.inputs[0])


class RECA_OT_setup_camera(Operator):
    """Set up camera with selected preset"""
    bl_idname = "reca.setup_camera"
    bl_label = "Setup Camera"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sb = context.scene.reca_scene_builder
        preset = sb.camera_preset

        # Remove existing RECA cameras
        for obj in list(bpy.data.objects):
            if obj.name.startswith("RECA_Camera"):
                bpy.data.objects.remove(obj, do_unlink=True)

        bpy.ops.object.camera_add(location=(7, -6, 5),
                                  rotation=(math.radians(60), 0, math.radians(45)))
        cam = bpy.context.active_object
        cam.name = "RECA_Camera"
        context.scene.camera = cam

        # Resolution
        context.scene.render.resolution_x = sb.res_x
        context.scene.render.resolution_y = sb.res_y

        if preset == 'PERSPECTIVE':
            cam.data.type = 'PERSP'
            cam.data.lens = 50
        elif preset == 'ORTHO':
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = 10
        elif preset == 'PORTRAIT':
            cam.data.type = 'PERSP'
            cam.data.lens = 85
            cam.data.dof.use_dof = True
            cam.data.dof.aperture_fstop = 1.8
        elif preset == 'WIDE':
            cam.data.type = 'PERSP'
            cam.data.lens = 24
        elif preset == 'MACRO':
            cam.data.type = 'PERSP'
            cam.data.lens = 100
            cam.data.dof.use_dof = True
            cam.data.dof.aperture_fstop = 2.8
            cam.location = (2, -2, 1.5)
            cam.rotation_euler = (math.radians(70), 0, math.radians(35))
        elif preset == 'CINEMATIC':
            cam.data.type = 'PERSP'
            cam.data.lens = 50
            context.scene.render.resolution_x = sb.res_x
            context.scene.render.resolution_y = int(sb.res_x / 2.39)

        self.report({'INFO'}, f"Camera: {preset}")
        return {'FINISHED'}


class RECA_OT_setup_environment(Operator):
    """Create environment / backdrop"""
    bl_idname = "reca.setup_environment"
    bl_label = "Setup Environment"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sb = context.scene.reca_scene_builder
        preset = sb.env_preset

        # Remove old RECA env objects
        for obj in list(bpy.data.objects):
            if obj.name.startswith("RECA_Env"):
                bpy.data.objects.remove(obj, do_unlink=True)

        if preset == 'NONE':
            self.report({'INFO'}, "Environment cleared")
            return {'FINISHED'}

        if preset == 'INFINITE_FLOOR':
            self._infinite_floor(context, sb)
        elif preset == 'CYCLORAMA':
            self._cyclorama(context, sb)
        elif preset == 'GRADIENT_BG':
            self._gradient_bg(context, sb)
        elif preset == 'TURNTABLE':
            self._turntable(context, sb)

        self.report({'INFO'}, f"Environment: {preset}")
        return {'FINISHED'}

    def _make_material(self, name, color, glossy=0.0):
        return make_principled_material(name, base_color=color, roughness=1.0 - glossy)

    def _infinite_floor(self, context, sb):
        bpy.ops.mesh.primitive_plane_add(size=sb.floor_size, location=(0, 0, 0))
        floor = bpy.context.active_object
        floor.name = "RECA_Env_Floor"
        mat = self._make_material("RECA_Floor_Mat", sb.env_color, sb.floor_glossy)
        floor.data.materials.append(mat)

    def _cyclorama(self, context, sb):
        size = sb.floor_size
        # Floor
        bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
        floor = bpy.context.active_object
        floor.name = "RECA_Env_Cyclo_Floor"

        # Back wall via curve
        bpy.ops.mesh.primitive_plane_add(size=size,
                                         location=(0, size / 2, size / 2),
                                         rotation=(math.radians(90), 0, 0))
        wall = bpy.context.active_object
        wall.name = "RECA_Env_Cyclo_Wall"

        mat = self._make_material("RECA_Cyclo_Mat", sb.env_color)
        floor.data.materials.append(mat)
        wall.data.materials.append(mat)

    def _gradient_bg(self, context, sb):
        world = context.scene.world
        if world is None:
            world = bpy.data.worlds.new("RECA_World")
            context.scene.world = world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()

        tex_coord = nodes.new('ShaderNodeTexCoord')
        mapping = nodes.new('ShaderNodeMapping')
        gradient = nodes.new('ShaderNodeTexGradient')
        ramp = nodes.new('ShaderNodeValToRGB')
        bg = nodes.new('ShaderNodeBackground')
        output = nodes.new('ShaderNodeOutputWorld')

        # Color ramp
        ramp.color_ramp.elements[0].color = (*sb.env_color, 1.0)
        ramp.color_ramp.elements[1].color = (*sb.env_color_2, 1.0)

        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        links.new(mapping.outputs['Vector'], gradient.inputs['Vector'])
        links.new(gradient.outputs['Color'], ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'], bg.inputs['Color'])
        links.new(bg.outputs['Background'], output.inputs['Surface'])

    def _turntable(self, context, sb):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=sb.floor_size / 4,
            depth=0.1,
            location=(0, 0, -0.05),
        )
        turntable = bpy.context.active_object
        turntable.name = "RECA_Env_Turntable"
        mat = self._make_material("RECA_Turntable_Mat", sb.env_color, sb.floor_glossy)
        turntable.data.materials.append(mat)


class RECA_OT_quick_scene_setup(Operator):
    """One-click full scene setup (lighting + camera + environment)"""
    bl_idname = "reca.quick_scene_setup"
    bl_label = "Quick Setup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sb = context.scene.reca_scene_builder
        if sb.clear_scene_first:
            bpy.ops.reca.clear_scene()
        if sb.add_lights:
            bpy.ops.reca.setup_lighting()
        if sb.add_camera:
            bpy.ops.reca.setup_camera()
        if sb.add_environment:
            bpy.ops.reca.setup_environment()
        self.report({'INFO'}, "Scene setup complete")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  Save/Load Preset
# ─────────────────────────────────────────────

class RECA_OT_save_scene_preset(Operator):
    """Save current scene builder settings as a preset"""
    bl_idname = "reca.save_scene_preset"
    bl_label = "Save Preset"

    preset_name: StringProperty(name="Preset Name", default="My Preset")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        import json, os
        sb = context.scene.reca_scene_builder
        data = {
            'lighting_preset': sb.lighting_preset,
            'camera_preset': sb.camera_preset,
            'env_preset': sb.env_preset,
            'env_color': list(sb.env_color),
            'env_color_2': list(sb.env_color_2),
            'floor_size': sb.floor_size,
            'floor_glossy': sb.floor_glossy,
            'res_x': sb.res_x,
            'res_y': sb.res_y,
        }
        preset_dir = os.path.join(bpy.utils.user_resource('CONFIG'), "reca", "presets")
        os.makedirs(preset_dir, exist_ok=True)
        filepath = os.path.join(preset_dir, f"{self.preset_name}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        self.report({'INFO'}, f"Preset saved: {self.preset_name}")
        return {'FINISHED'}


class RECA_OT_load_scene_preset(Operator):
    """Load a scene builder preset"""
    bl_idname = "reca.load_scene_preset"
    bl_label = "Load Preset"

    preset_name: StringProperty(name="Preset Name")

    def execute(self, context):
        import json, os
        sb = context.scene.reca_scene_builder
        preset_dir = os.path.join(bpy.utils.user_resource('CONFIG'), "reca", "presets")
        filepath = os.path.join(preset_dir, f"{self.preset_name}.json")
        if not os.path.isfile(filepath):
            self.report({'ERROR'}, f"Preset not found: {self.preset_name}")
            return {'CANCELLED'}
        with open(filepath, 'r') as f:
            data = json.load(f)
        for key, value in data.items():
            if hasattr(sb, key):
                setattr(sb, key, value if not isinstance(value, list) else tuple(value))
        self.report({'INFO'}, f"Preset loaded: {self.preset_name}")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UI Draw
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    sb = context.scene.reca_scene_builder

    # Quick Setup
    box = layout.box()
    box.label(text="Quick Setup", icon='SCENE_DATA')
    row = box.row(align=True)
    row.prop(sb, "clear_scene_first", toggle=True, icon='TRASH')
    row.prop(sb, "add_lights", toggle=True, icon='LIGHT')
    row.prop(sb, "add_camera", toggle=True, icon='CAMERA_DATA')
    row = box.row(align=True)
    row.prop(sb, "add_environment", toggle=True, icon='WORLD')
    box.operator("reca.quick_scene_setup", icon='PLAY')

    layout.separator()

    # Lighting
    box = layout.box()
    box.label(text="Lighting", icon='LIGHT')
    box.prop(sb, "lighting_preset", text="")
    box.operator("reca.setup_lighting", icon='LIGHT_AREA')

    # Camera
    box = layout.box()
    box.label(text="Camera", icon='CAMERA_DATA')
    box.prop(sb, "camera_preset", text="")
    row = box.row(align=True)
    row.prop(sb, "res_x")
    row.prop(sb, "res_y")
    box.operator("reca.setup_camera", icon='OUTLINER_OB_CAMERA')

    # Environment
    box = layout.box()
    box.label(text="Environment", icon='WORLD')
    box.prop(sb, "env_preset", text="")
    if sb.env_preset != 'NONE':
        box.prop(sb, "env_color")
        if sb.env_preset == 'GRADIENT_BG':
            box.prop(sb, "env_color_2")
        if sb.env_preset in ('INFINITE_FLOOR', 'CYCLORAMA', 'TURNTABLE'):
            box.prop(sb, "floor_size")
            box.prop(sb, "floor_glossy")
    box.operator("reca.setup_environment", icon='WORLD_DATA')

    layout.separator()
    box = layout.box()
    box.label(text="Presets", icon='PRESET')
    row = box.row(align=True)
    row.operator("reca.save_scene_preset", icon='FILE_TICK')
    row.operator("reca.load_scene_preset", icon='FILE_FOLDER')

    layout.separator()
    layout.operator("reca.clear_scene", icon='TRASH', text="Clear Entire Scene")


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_scene_builder,
    RECA_OT_clear_scene,
    RECA_OT_setup_lighting,
    RECA_OT_setup_camera,
    RECA_OT_setup_environment,
    RECA_OT_quick_scene_setup,
    RECA_OT_save_scene_preset,
    RECA_OT_load_scene_preset,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_scene_builder = PointerProperty(type=RECA_PG_scene_builder)


def unregister():
    del bpy.types.Scene.reca_scene_builder
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
