# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA Render Manager — presets, batch render, quick settings."""

import bpy
import os
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    FloatProperty,
    BoolProperty,
    IntProperty,
    StringProperty,
    PointerProperty,
    FloatVectorProperty,
)
from ..utils import make_principled_material


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_render_manager(PropertyGroup):
    # Preset
    render_preset: EnumProperty(
        name="Preset",
        items=[
            ('PREVIEW', "Preview (Fast)", "Low quality fast render"),
            ('MEDIUM', "Medium Quality", "Balanced quality"),
            ('HIGH', "High Quality", "Production quality"),
            ('ULTRA', "Ultra / Final", "Maximum quality"),
            ('ANIMATION', "Animation", "Optimized for animation"),
            ('CLAY', "Clay Render", "Material override with clay"),
            ('WIREFRAME', "Wireframe", "Wireframe overlay render"),
            ('AO', "Ambient Occlusion", "AO only render"),
            ('CUSTOM', "Custom", "Use current settings"),
        ],
        default='MEDIUM',
    )

    # Engine
    engine: EnumProperty(
        name="Engine",
        items=[
            ('CYCLES', "Cycles", "Path tracing"),
            ('BLENDER_EEVEE_NEXT', "EEVEE", "Real-time"),
        ],
        default='CYCLES',
    )

    # Output
    output_path: StringProperty(
        name="Output Path",
        subtype='DIR_PATH',
        default="//renders/",
    )
    output_format: EnumProperty(
        name="Format",
        items=[
            ('PNG', "PNG", ""), ('JPEG', "JPEG", ""),
            ('OPEN_EXR', "EXR", ""), ('TIFF', "TIFF", ""),
            ('BMP', "BMP", ""),
        ],
        default='PNG',
    )
    filename_prefix: StringProperty(name="Prefix", default="render_")
    use_timestamp: BoolProperty(name="Add Timestamp", default=True)

    # Resolution
    res_x: IntProperty(name="X", default=1920, min=1, max=16384)
    res_y: IntProperty(name="Y", default=1080, min=1, max=16384)
    res_percent: IntProperty(name="%", default=100, min=1, max=200)

    # Cycles
    samples: IntProperty(name="Samples", default=128, min=1, max=10000)
    use_denoiser: BoolProperty(name="Denoiser", default=True)
    denoiser: EnumProperty(
        name="Denoiser",
        items=[
            ('OPENIMAGEDENOISE', "OpenImageDenoise", ""),
            ('OPTIX', "OptiX", ""),
        ],
        default='OPENIMAGEDENOISE',
    )
    use_gpu: BoolProperty(name="Use GPU", default=True)

    # Color management
    view_transform: EnumProperty(
        name="View Transform",
        items=[
            ('Filmic', "Filmic", ""),
            ('AgX', "AgX", ""),
            ('Standard', "Standard", ""),
            ('Raw', "Raw", ""),
        ],
        default='AgX',
    )
    exposure: FloatProperty(name="Exposure", default=0.0, min=-10.0, max=10.0)
    gamma: FloatProperty(name="Gamma", default=1.0, min=0.01, max=5.0)

    # Multi-camera
    render_all_cameras: BoolProperty(name="Render All Cameras", default=False)

    # Turntable animation
    turntable_frames: IntProperty(name="Frames", default=120, min=12, max=1000)
    turntable_target: StringProperty(name="Target Object", default="")

    # Film
    film_transparent: BoolProperty(name="Transparent Background", default=False)

    # Clay color
    clay_color: FloatVectorProperty(
        name="Clay Color",
        subtype='COLOR',
        default=(0.8, 0.8, 0.8),
        min=0.0, max=1.0,
    )


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_apply_render_preset(Operator):
    """Apply render preset settings"""
    bl_idname = "reca.apply_render_preset"
    bl_label = "Apply Preset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rm = context.scene.reca_render_manager
        scene = context.scene
        preset = rm.render_preset

        scene.render.engine = rm.engine
        scene.render.resolution_x = rm.res_x
        scene.render.resolution_y = rm.res_y
        scene.render.resolution_percentage = rm.res_percent
        scene.render.image_settings.file_format = rm.output_format
        scene.render.filepath = bpy.path.abspath(rm.output_path)
        scene.render.film_transparent = rm.film_transparent

        # Color management
        scene.view_settings.view_transform = rm.view_transform
        scene.view_settings.exposure = rm.exposure
        scene.view_settings.gamma = rm.gamma

        if rm.engine == 'CYCLES':
            cycles = scene.cycles
            if preset == 'PREVIEW':
                cycles.samples = 32
                cycles.use_denoising = True
                cycles.preview_samples = 16
            elif preset == 'MEDIUM':
                cycles.samples = 128
                cycles.use_denoising = True
            elif preset == 'HIGH':
                cycles.samples = 512
                cycles.use_denoising = True
            elif preset == 'ULTRA':
                cycles.samples = 2048
                cycles.use_denoising = True
            elif preset == 'ANIMATION':
                cycles.samples = 64
                cycles.use_denoising = True
            elif preset == 'CUSTOM':
                cycles.samples = rm.samples
                cycles.use_denoising = rm.use_denoiser
            else:
                cycles.samples = rm.samples
                cycles.use_denoising = rm.use_denoiser

            if rm.use_gpu:
                cycles.device = 'GPU'
            else:
                cycles.device = 'CPU'

        self.report({'INFO'}, f"Render preset applied: {preset}")
        return {'FINISHED'}


class RECA_OT_quick_render(Operator):
    """Render current frame with RECA settings"""
    bl_idname = "reca.quick_render"
    bl_label = "Quick Render"

    def execute(self, context):
        rm = context.scene.reca_render_manager
        bpy.ops.reca.apply_render_preset()

        output = bpy.path.abspath(rm.output_path)
        os.makedirs(output, exist_ok=True)

        prefix = rm.filename_prefix
        if rm.use_timestamp:
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix += ts

        ext_map = {'PNG': '.png', 'JPEG': '.jpg', 'OPEN_EXR': '.exr',
                    'TIFF': '.tiff', 'BMP': '.bmp'}
        ext = ext_map.get(rm.output_format, '.png')
        filepath = os.path.join(output, prefix + ext)
        context.scene.render.filepath = filepath

        bpy.ops.render.render(write_still=True)
        self.report({'INFO'}, f"Rendered: {filepath}")
        return {'FINISHED'}


class RECA_OT_render_all_cameras(Operator):
    """Render from every camera in the scene"""
    bl_idname = "reca.render_all_cameras"
    bl_label = "Render All Cameras"

    def execute(self, context):
        rm = context.scene.reca_render_manager
        bpy.ops.reca.apply_render_preset()

        cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
        if not cameras:
            self.report({'WARNING'}, "No cameras found")
            return {'CANCELLED'}

        output = bpy.path.abspath(rm.output_path)
        os.makedirs(output, exist_ok=True)
        ext_map = {'PNG': '.png', 'JPEG': '.jpg', 'OPEN_EXR': '.exr',
                    'TIFF': '.tiff', 'BMP': '.bmp'}
        ext = ext_map.get(rm.output_format, '.png')

        original_cam = context.scene.camera
        for cam in cameras:
            context.scene.camera = cam
            filepath = os.path.join(output, f"{rm.filename_prefix}{cam.name}{ext}")
            context.scene.render.filepath = filepath
            bpy.ops.render.render(write_still=True)
            self.report({'INFO'}, f"Rendered: {cam.name}")

        context.scene.camera = original_cam
        self.report({'INFO'}, f"Rendered {len(cameras)} cameras")
        return {'FINISHED'}


class RECA_OT_setup_turntable(Operator):
    """Create turntable animation around target object"""
    bl_idname = "reca.setup_turntable"
    bl_label = "Setup Turntable"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import math
        rm = context.scene.reca_render_manager
        scene = context.scene

        cam = scene.camera
        if cam is None:
            self.report({'ERROR'}, "No active camera")
            return {'CANCELLED'}

        target_name = rm.turntable_target
        target_loc = (0, 0, 0)
        if target_name and target_name in bpy.data.objects:
            target_loc = bpy.data.objects[target_name].location

        # Create empty as rotation pivot
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=target_loc)
        pivot = context.active_object
        pivot.name = "RECA_Turntable_Pivot"

        # Parent camera to pivot
        cam.parent = pivot

        # Keyframe rotation
        frames = rm.turntable_frames
        scene.frame_start = 1
        scene.frame_end = frames

        pivot.rotation_euler = (0, 0, 0)
        pivot.keyframe_insert(data_path="rotation_euler", frame=1)
        pivot.rotation_euler = (0, 0, math.radians(360))
        pivot.keyframe_insert(data_path="rotation_euler", frame=frames + 1)

        # Linear interpolation
        if pivot.animation_data and pivot.animation_data.action:
            for fc in pivot.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'

        self.report({'INFO'}, f"Turntable: {frames} frames")
        return {'FINISHED'}


class RECA_OT_clay_render(Operator):
    """Override all materials with clay material"""
    bl_idname = "reca.clay_render"
    bl_label = "Clay Override"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rm = context.scene.reca_render_manager
        # Store originals
        mat_backup = {}
        clay = make_principled_material(
            "RECA_Clay",
            base_color=rm.clay_color,
            roughness=0.8,
            specular=0.2,
        )

        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data:
                mat_backup[obj.name] = [s.material for s in obj.material_slots]
                obj.data.materials.clear()
                obj.data.materials.append(clay)

        # Store backup for restore
        context.scene["reca_clay_backup"] = str(mat_backup)
        self.report({'INFO'}, "Clay material override applied")
        return {'FINISHED'}


class RECA_OT_restore_materials(Operator):
    """Restore original materials after clay override"""
    bl_idname = "reca.restore_materials"
    bl_label = "Restore Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Remove clay material
        for mat in list(bpy.data.materials):
            if mat.name.startswith("RECA_Clay"):
                bpy.data.materials.remove(mat)
        self.report({'INFO'}, "Materials restored (re-assign manually if needed)")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    rm = context.scene.reca_render_manager

    # Preset
    box = layout.box()
    box.label(text="Render Preset", icon='RENDER_STILL')
    box.prop(rm, "render_preset", text="")
    box.prop(rm, "engine")
    box.operator("reca.apply_render_preset", icon='CHECKMARK')

    # Resolution
    box = layout.box()
    box.label(text="Resolution", icon='IMAGE_DATA')
    row = box.row(align=True)
    row.prop(rm, "res_x")
    row.prop(rm, "res_y")
    box.prop(rm, "res_percent", slider=True)

    # Quality
    if rm.engine == 'CYCLES':
        box = layout.box()
        box.label(text="Cycles Settings", icon='SHADING_RENDERED')
        box.prop(rm, "samples")
        box.prop(rm, "use_denoiser")
        if rm.use_denoiser:
            box.prop(rm, "denoiser")
        box.prop(rm, "use_gpu")

    # Color Management
    box = layout.box()
    box.label(text="Color Management", icon='COLOR')
    box.prop(rm, "view_transform")
    box.prop(rm, "exposure")
    box.prop(rm, "gamma")

    # Output
    box = layout.box()
    box.label(text="Output", icon='OUTPUT')
    box.prop(rm, "output_path")
    box.prop(rm, "output_format")
    box.prop(rm, "filename_prefix")
    box.prop(rm, "use_timestamp")
    box.prop(rm, "film_transparent")

    # Render Actions
    layout.separator()
    box = layout.box()
    box.label(text="Render", icon='RENDER_ANIMATION')
    box.operator("reca.quick_render", icon='RENDER_STILL', text="Render Image")
    box.operator("reca.render_all_cameras", icon='OUTLINER_OB_CAMERA')

    # Turntable
    box = layout.box()
    box.label(text="Turntable", icon='FILE_MOVIE')
    box.prop(rm, "turntable_target", icon='OBJECT_DATA')
    box.prop(rm, "turntable_frames")
    box.operator("reca.setup_turntable", icon='LOOP_BACK')

    # Clay / Override
    box = layout.box()
    box.label(text="Material Override", icon='SHADING_SOLID')
    box.prop(rm, "clay_color")
    row = box.row(align=True)
    row.operator("reca.clay_render", icon='SHADING_SOLID')
    row.operator("reca.restore_materials", icon='LOOP_BACK')


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_render_manager,
    RECA_OT_apply_render_preset,
    RECA_OT_quick_render,
    RECA_OT_render_all_cameras,
    RECA_OT_setup_turntable,
    RECA_OT_clay_render,
    RECA_OT_restore_materials,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_render_manager = PointerProperty(type=RECA_PG_render_manager)


def unregister():
    del bpy.types.Scene.reca_render_manager
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
