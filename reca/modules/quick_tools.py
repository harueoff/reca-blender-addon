# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA Quick Tools — everyday utilities for faster 3D workflow."""

import bpy
import math
from mathutils import Vector, Matrix
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    FloatProperty,
    BoolProperty,
    IntProperty,
    StringProperty,
    PointerProperty,
)


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_quick_tools(PropertyGroup):
    # Align
    align_axis: EnumProperty(
        name="Axis",
        items=[
            ('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", ""),
        ],
        default='X',
    )
    align_mode: EnumProperty(
        name="Align To",
        items=[
            ('MIN', "Min", "Align to minimum"),
            ('MAX', "Max", "Align to maximum"),
            ('CENTER', "Center", "Align to center"),
            ('CURSOR', "3D Cursor", "Align to cursor"),
            ('ACTIVE', "Active Object", "Align to active object"),
            ('ORIGIN', "World Origin", "Align to (0,0,0)"),
        ],
        default='CENTER',
    )
    align_distribute: BoolProperty(name="Distribute Evenly", default=False)

    # Origin
    origin_mode: EnumProperty(
        name="Set Origin",
        items=[
            ('CENTER', "Center of Mass", ""),
            ('BOTTOM', "Bottom Center", ""),
            ('TOP', "Top Center", ""),
            ('CURSOR', "3D Cursor", ""),
            ('MIN_X', "Min X", ""),
            ('MAX_X', "Max X", ""),
        ],
        default='BOTTOM',
    )

    # Mirror
    mirror_axis: EnumProperty(
        name="Mirror Axis",
        items=[('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")],
        default='X',
    )

    # Random Transform
    rand_loc: FloatProperty(name="Location", default=0.5, min=0.0, max=50.0)
    rand_rot: FloatProperty(name="Rotation", default=15.0, min=0.0, max=360.0)
    rand_scale: FloatProperty(name="Scale", default=0.2, min=0.0, max=2.0)
    rand_uniform_scale: BoolProperty(name="Uniform Scale", default=True)
    rand_seed: IntProperty(name="Seed", default=42, min=0)

    # Selection tools
    select_by: EnumProperty(
        name="Select By",
        items=[
            ('TYPE', "Object Type", ""),
            ('NAME', "Name Contains", ""),
            ('MATERIAL', "Material Name", ""),
            ('VERTS', "Vertex Count", ""),
            ('FACES', "Face Count", ""),
            ('NO_MAT', "No Material", ""),
            ('HIDDEN', "Hidden Objects", ""),
        ],
        default='TYPE',
    )
    select_type: EnumProperty(
        name="Type",
        items=[
            ('MESH', "Mesh", ""), ('CURVE', "Curve", ""),
            ('LIGHT', "Light", ""), ('CAMERA', "Camera", ""),
            ('EMPTY', "Empty", ""), ('ARMATURE', "Armature", ""),
        ],
        default='MESH',
    )
    select_name: StringProperty(name="Contains", default="")
    select_min_verts: IntProperty(name="Min Verts", default=0)
    select_max_verts: IntProperty(name="Max Verts", default=1000000)

    # Copy attributes
    copy_attr: EnumProperty(
        name="Copy Attribute",
        items=[
            ('MATERIAL', "Materials", ""),
            ('MODIFIERS', "Modifiers", ""),
            ('TRANSFORM', "Transform", ""),
            ('CONSTRAINTS', "Constraints", ""),
            ('CUSTOM_PROPS', "Custom Properties", ""),
        ],
        default='MATERIAL',
    )


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_align_objects(Operator):
    """Align selected objects"""
    bl_idname = "reca.align_objects"
    bl_label = "Align Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        qt = context.scene.reca_quick_tools
        selected = context.selected_objects
        if len(selected) < 1:
            self.report({'WARNING'}, "Select at least one object")
            return {'CANCELLED'}

        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[qt.align_axis]

        if qt.align_distribute and len(selected) > 2:
            objs = sorted(selected, key=lambda o: o.location[axis_idx])
            start = objs[0].location[axis_idx]
            end = objs[-1].location[axis_idx]
            step = (end - start) / (len(objs) - 1) if len(objs) > 1 else 0
            for i, obj in enumerate(objs):
                obj.location[axis_idx] = start + i * step
            self.report({'INFO'}, f"Distributed {len(objs)} objects on {qt.align_axis}")
            return {'FINISHED'}

        # Target value
        if qt.align_mode == 'MIN':
            target = min(o.location[axis_idx] for o in selected)
        elif qt.align_mode == 'MAX':
            target = max(o.location[axis_idx] for o in selected)
        elif qt.align_mode == 'CENTER':
            vals = [o.location[axis_idx] for o in selected]
            target = (min(vals) + max(vals)) / 2
        elif qt.align_mode == 'CURSOR':
            target = context.scene.cursor.location[axis_idx]
        elif qt.align_mode == 'ACTIVE':
            if context.active_object:
                target = context.active_object.location[axis_idx]
            else:
                target = 0
        elif qt.align_mode == 'ORIGIN':
            target = 0

        for obj in selected:
            obj.location[axis_idx] = target

        self.report({'INFO'}, f"Aligned {len(selected)} objects")
        return {'FINISHED'}


class RECA_OT_set_origin(Operator):
    """Set origin point for selected objects"""
    bl_idname = "reca.set_origin"
    bl_label = "Set Origin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        qt = context.scene.reca_quick_tools
        mode = qt.origin_mode

        if mode == 'CENTER':
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
        elif mode == 'CURSOR':
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        elif mode == 'BOTTOM':
            for obj in context.selected_objects:
                if obj.type != 'MESH':
                    continue
                local_verts = [v.co for v in obj.data.vertices]
                if not local_verts:
                    continue
                min_z = min(v.z for v in local_verts)
                offset = obj.matrix_world @ Vector((0, 0, min_z)) - obj.matrix_world @ Vector((0, 0, 0))
                obj.data.transform(Matrix.Translation((0, 0, -min_z)))
                obj.matrix_world.translation += Vector((0, 0, min_z))
        elif mode == 'TOP':
            for obj in context.selected_objects:
                if obj.type != 'MESH':
                    continue
                local_verts = [v.co for v in obj.data.vertices]
                if not local_verts:
                    continue
                max_z = max(v.z for v in local_verts)
                obj.data.transform(Matrix.Translation((0, 0, -max_z)))
                obj.matrix_world.translation += Vector((0, 0, max_z))
        else:
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

        self.report({'INFO'}, f"Origin set: {mode}")
        return {'FINISHED'}


class RECA_OT_random_transform(Operator):
    """Apply random transform to selected objects"""
    bl_idname = "reca.random_transform"
    bl_label = "Randomize Transform"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import random
        qt = context.scene.reca_quick_tools
        random.seed(qt.rand_seed)

        for obj in context.selected_objects:
            if qt.rand_loc > 0:
                obj.location.x += random.uniform(-qt.rand_loc, qt.rand_loc)
                obj.location.y += random.uniform(-qt.rand_loc, qt.rand_loc)
                obj.location.z += random.uniform(-qt.rand_loc, qt.rand_loc)
            if qt.rand_rot > 0:
                r = math.radians(qt.rand_rot)
                obj.rotation_euler.x += random.uniform(-r, r)
                obj.rotation_euler.y += random.uniform(-r, r)
                obj.rotation_euler.z += random.uniform(-r, r)
            if qt.rand_scale > 0:
                if qt.rand_uniform_scale:
                    s = 1.0 + random.uniform(-qt.rand_scale, qt.rand_scale)
                    obj.scale *= s
                else:
                    obj.scale.x *= 1.0 + random.uniform(-qt.rand_scale, qt.rand_scale)
                    obj.scale.y *= 1.0 + random.uniform(-qt.rand_scale, qt.rand_scale)
                    obj.scale.z *= 1.0 + random.uniform(-qt.rand_scale, qt.rand_scale)

        self.report({'INFO'}, f"Randomized {len(context.selected_objects)} objects")
        return {'FINISHED'}


class RECA_OT_smart_select(Operator):
    """Select objects by criteria"""
    bl_idname = "reca.smart_select"
    bl_label = "Smart Select"

    def execute(self, context):
        qt = context.scene.reca_quick_tools
        bpy.ops.object.select_all(action='DESELECT')
        count = 0

        for obj in bpy.data.objects:
            match = False
            if qt.select_by == 'TYPE':
                match = obj.type == qt.select_type
            elif qt.select_by == 'NAME':
                match = qt.select_name.lower() in obj.name.lower()
            elif qt.select_by == 'MATERIAL':
                for slot in obj.material_slots:
                    if slot.material and qt.select_name.lower() in slot.material.name.lower():
                        match = True
                        break
            elif qt.select_by == 'VERTS':
                if obj.type == 'MESH' and obj.data:
                    vc = len(obj.data.vertices)
                    match = qt.select_min_verts <= vc <= qt.select_max_verts
            elif qt.select_by == 'FACES':
                if obj.type == 'MESH' and obj.data:
                    fc = len(obj.data.polygons)
                    match = qt.select_min_verts <= fc <= qt.select_max_verts
            elif qt.select_by == 'NO_MAT':
                match = len(obj.material_slots) == 0
            elif qt.select_by == 'HIDDEN':
                match = obj.hide_viewport or obj.hide_get()

            if match:
                obj.select_set(True)
                count += 1

        self.report({'INFO'}, f"Selected {count} objects")
        return {'FINISHED'}


class RECA_OT_copy_attributes(Operator):
    """Copy attributes from active to selected objects"""
    bl_idname = "reca.copy_attributes"
    bl_label = "Copy Attributes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and len(context.selected_objects) > 1

    def execute(self, context):
        qt = context.scene.reca_quick_tools
        source = context.active_object
        targets = [o for o in context.selected_objects if o != source]
        attr = qt.copy_attr

        for target in targets:
            if attr == 'MATERIAL':
                target.data.materials.clear()
                for slot in source.material_slots:
                    target.data.materials.append(slot.material)
            elif attr == 'MODIFIERS':
                for mod in source.modifiers:
                    new_mod = target.modifiers.new(mod.name, mod.type)
                    for prop in dir(mod):
                        if not prop.startswith('_') and prop not in ('bl_rna', 'rna_type', 'type', 'name'):
                            try:
                                setattr(new_mod, prop, getattr(mod, prop))
                            except (AttributeError, TypeError):
                                pass
            elif attr == 'TRANSFORM':
                target.location = source.location.copy()
                target.rotation_euler = source.rotation_euler.copy()
                target.scale = source.scale.copy()
            elif attr == 'CONSTRAINTS':
                for con in target.constraints:
                    target.constraints.remove(con)
                for con in source.constraints:
                    new_con = target.constraints.new(con.type)
                    for prop in dir(con):
                        if not prop.startswith('_') and prop not in ('bl_rna', 'rna_type', 'type', 'name'):
                            try:
                                setattr(new_con, prop, getattr(con, prop))
                            except (AttributeError, TypeError):
                                pass
            elif attr == 'CUSTOM_PROPS':
                for key in source.keys():
                    if key not in {'_RNA_UI', 'cycles'}:
                        target[key] = source[key]

        self.report({'INFO'}, f"Copied {attr} to {len(targets)} objects")
        return {'FINISHED'}


class RECA_OT_apply_all_transforms(Operator):
    """Apply all transforms to selected objects"""
    bl_idname = "reca.apply_all_transforms"
    bl_label = "Apply All Transforms"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for obj in context.selected_objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            count += 1
        self.report({'INFO'}, f"Applied transforms: {count} objects")
        return {'FINISHED'}


class RECA_OT_mirror_object(Operator):
    """Mirror selected objects on axis"""
    bl_idname = "reca.mirror_object"
    bl_label = "Mirror Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        qt = context.scene.reca_quick_tools
        axis = qt.mirror_axis
        for obj in context.selected_objects:
            mod = obj.modifiers.new("RECA_Mirror", 'MIRROR')
            mod.use_axis[0] = (axis == 'X')
            mod.use_axis[1] = (axis == 'Y')
            mod.use_axis[2] = (axis == 'Z')
        self.report({'INFO'}, f"Mirror modifier added on {axis}")
        return {'FINISHED'}


class RECA_OT_flatten_hierarchy(Operator):
    """Unparent all selected objects while keeping transforms"""
    bl_idname = "reca.flatten_hierarchy"
    bl_label = "Flatten Hierarchy"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for obj in context.selected_objects:
            if obj.parent:
                mat = obj.matrix_world.copy()
                obj.parent = None
                obj.matrix_world = mat
                count += 1
        self.report({'INFO'}, f"Unparented {count} objects")
        return {'FINISHED'}


class RECA_OT_merge_objects(Operator):
    """Join all selected mesh objects into one"""
    bl_idname = "reca.merge_objects"
    bl_label = "Merge Objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len([o for o in context.selected_objects if o.type == 'MESH']) > 1

    def execute(self, context):
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        bpy.ops.object.select_all(action='DESELECT')
        for m in meshes:
            m.select_set(True)
        context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        self.report({'INFO'}, f"Merged {len(meshes)} objects")
        return {'FINISHED'}


class RECA_OT_separate_by_loose(Operator):
    """Separate mesh by loose parts"""
    bl_idname = "reca.separate_by_loose"
    bl_label = "Separate by Loose Parts"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, "Separated by loose parts")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    qt = context.scene.reca_quick_tools

    # Align & Distribute
    box = layout.box()
    box.label(text="Align & Distribute", icon='SNAP_ON')
    row = box.row(align=True)
    row.prop(qt, "align_axis", expand=True)
    box.prop(qt, "align_mode")
    box.prop(qt, "align_distribute")
    box.operator("reca.align_objects", icon='ALIGN_CENTER')

    # Origin
    box = layout.box()
    box.label(text="Origin", icon='OBJECT_ORIGIN')
    box.prop(qt, "origin_mode", text="")
    box.operator("reca.set_origin", icon='PIVOT_BOUNDBOX')

    # Transform Tools
    box = layout.box()
    box.label(text="Transform", icon='OBJECT_DATA')
    box.operator("reca.apply_all_transforms", icon='CHECKMARK')
    row = box.row(align=True)
    row.prop(qt, "mirror_axis", expand=True)
    box.operator("reca.mirror_object", icon='MOD_MIRROR')
    box.operator("reca.flatten_hierarchy", icon='CON_CHILDOF')

    # Randomize
    box = layout.box()
    box.label(text="Randomize", icon='MOD_NOISE')
    box.prop(qt, "rand_seed")
    box.prop(qt, "rand_loc")
    box.prop(qt, "rand_rot")
    box.prop(qt, "rand_scale")
    box.prop(qt, "rand_uniform_scale")
    box.operator("reca.random_transform", icon='FORCE_TURBULENCE')

    # Smart Select
    box = layout.box()
    box.label(text="Smart Select", icon='RESTRICT_SELECT_OFF')
    box.prop(qt, "select_by")
    if qt.select_by == 'TYPE':
        box.prop(qt, "select_type")
    elif qt.select_by in ('NAME', 'MATERIAL'):
        box.prop(qt, "select_name")
    elif qt.select_by in ('VERTS', 'FACES'):
        row = box.row(align=True)
        row.prop(qt, "select_min_verts", text="Min")
        row.prop(qt, "select_max_verts", text="Max")
    box.operator("reca.smart_select", icon='VIEWZOOM')

    # Copy Attributes
    box = layout.box()
    box.label(text="Copy Attributes", icon='COPYDOWN')
    box.prop(qt, "copy_attr", text="")
    box.operator("reca.copy_attributes", icon='PASTEDOWN')

    # Object Operations
    box = layout.box()
    box.label(text="Object Ops", icon='OBJECT_DATAMODE')
    box.operator("reca.merge_objects", icon='SELECT_EXTEND')
    box.operator("reca.separate_by_loose", icon='SELECT_SUBTRACT')


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_quick_tools,
    RECA_OT_align_objects,
    RECA_OT_set_origin,
    RECA_OT_random_transform,
    RECA_OT_smart_select,
    RECA_OT_copy_attributes,
    RECA_OT_apply_all_transforms,
    RECA_OT_mirror_object,
    RECA_OT_flatten_hierarchy,
    RECA_OT_merge_objects,
    RECA_OT_separate_by_loose,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_quick_tools = PointerProperty(type=RECA_PG_quick_tools)


def unregister():
    del bpy.types.Scene.reca_quick_tools
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
