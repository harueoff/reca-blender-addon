# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA Batch Processor — bulk operations on files and objects."""

import bpy
import os
import glob as _glob
from bpy.types import Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    PointerProperty,
    CollectionProperty,
)


# ─────────────────────────────────────────────
#  Data
# ─────────────────────────────────────────────

class RECA_PG_batch_file_item(PropertyGroup):
    filepath: StringProperty(name="File")
    selected: BoolProperty(name="Selected", default=True)
    status: StringProperty(name="Status", default="Pending")


class RECA_PG_batch_processor(PropertyGroup):
    # Source
    source_dir: StringProperty(
        name="Source Directory",
        subtype='DIR_PATH',
        default="//",
    )
    output_dir: StringProperty(
        name="Output Directory",
        subtype='DIR_PATH',
        default="//batch_output/",
    )
    file_pattern: StringProperty(
        name="File Pattern",
        default="*.blend",
        description="Glob pattern for files (e.g. *.blend, *.obj, *.fbx)",
    )

    # Operations
    operation: EnumProperty(
        name="Operation",
        items=[
            ('CONVERT', "Convert Format", "Convert between 3D file formats"),
            ('RENDER', "Batch Render", "Render all .blend files"),
            ('INFO', "Scene Info", "Extract scene statistics"),
            ('RENAME_OBJ', "Rename Objects", "Rename objects in .blend files"),
            ('OPTIMIZE', "Optimize Meshes", "Decimate/optimize meshes"),
            ('PURGE', "Purge Unused", "Remove orphan data from .blend files"),
            ('EXPORT_SEP', "Export Separated", "Export each object as separate file"),
        ],
        default='CONVERT',
    )

    # Convert options
    convert_format: EnumProperty(
        name="Target Format",
        items=[
            ('OBJ', ".obj", "Wavefront OBJ"),
            ('FBX', ".fbx", "Autodesk FBX"),
            ('GLB', ".glb", "glTF Binary"),
            ('GLTF', ".gltf", "glTF"),
            ('STL', ".stl", "STL"),
            ('USD', ".usd", "Universal Scene Description"),
            ('BLEND', ".blend", "Blender file"),
        ],
        default='FBX',
    )

    # Optimize options
    decimate_ratio: FloatProperty(
        name="Decimate Ratio",
        default=0.5,
        min=0.01,
        max=1.0,
    )

    # Rename options
    rename_prefix: StringProperty(name="Prefix", default="")
    rename_suffix: StringProperty(name="Suffix", default="")
    rename_mode: EnumProperty(
        name="Rename Mode",
        items=[
            ('PREFIX', "Add Prefix", ""),
            ('SUFFIX', "Add Suffix", ""),
            ('BY_TYPE', "By Type (mesh_001, light_001...)", ""),
            ('LOWERCASE', "Lowercase All", ""),
            ('REPLACE', "Find & Replace", ""),
        ],
        default='BY_TYPE',
    )
    rename_find: StringProperty(name="Find", default="")
    rename_replace: StringProperty(name="Replace", default="")

    # Render
    render_engine: EnumProperty(
        name="Render Engine",
        items=[
            ('CYCLES', "Cycles", ""),
            ('BLENDER_EEVEE_NEXT', "EEVEE", ""),
        ],
        default='CYCLES',
    )
    render_samples: IntProperty(name="Samples", default=128, min=1, max=10000)

    # Files list
    files: CollectionProperty(type=RECA_PG_batch_file_item)
    files_index: IntProperty(default=0)

    # Progress
    progress: FloatProperty(name="Progress", default=0.0, min=0.0, max=100.0, subtype='PERCENTAGE')
    status_text: StringProperty(name="Status", default="Ready")


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_batch_scan_files(Operator):
    """Scan source directory for files matching pattern"""
    bl_idname = "reca.batch_scan_files"
    bl_label = "Scan Files"

    def execute(self, context):
        bp = context.scene.reca_batch_processor
        bp.files.clear()

        source = bpy.path.abspath(bp.source_dir)
        if not os.path.isdir(source):
            self.report({'ERROR'}, f"Directory not found: {source}")
            return {'CANCELLED'}

        pattern = os.path.join(source, bp.file_pattern)
        found = sorted(_glob.glob(pattern))
        for f in found:
            item = bp.files.add()
            item.filepath = f
            item.selected = True
            item.status = "Pending"

        bp.status_text = f"Found {len(found)} files"
        self.report({'INFO'}, bp.status_text)
        return {'FINISHED'}


class RECA_OT_batch_convert(Operator):
    """Convert files to target format"""
    bl_idname = "reca.batch_convert"
    bl_label = "Batch Convert"

    def execute(self, context):
        bp = context.scene.reca_batch_processor
        output = bpy.path.abspath(bp.output_dir)
        os.makedirs(output, exist_ok=True)

        files = [f for f in bp.files if f.selected]
        total = len(files)
        if total == 0:
            self.report({'WARNING'}, "No files selected")
            return {'CANCELLED'}

        for i, item in enumerate(files):
            bp.progress = (i / total) * 100
            bp.status_text = f"Converting {i + 1}/{total}: {os.path.basename(item.filepath)}"

            ext = os.path.splitext(item.filepath)[1].lower()
            try:
                # Open or import
                if ext == '.blend':
                    bpy.ops.wm.open_mainfile(filepath=item.filepath)
                elif ext == '.obj':
                    bpy.ops.wm.obj_import(filepath=item.filepath)
                elif ext == '.fbx':
                    bpy.ops.import_scene.fbx(filepath=item.filepath)
                elif ext in ('.glb', '.gltf'):
                    bpy.ops.import_scene.gltf(filepath=item.filepath)
                elif ext == '.stl':
                    bpy.ops.wm.stl_import(filepath=item.filepath)

                base = os.path.splitext(os.path.basename(item.filepath))[0]
                fmt = bp.convert_format
                out_path = os.path.join(output, base)

                if fmt == 'OBJ':
                    bpy.ops.wm.obj_export(filepath=out_path + ".obj")
                elif fmt == 'FBX':
                    bpy.ops.export_scene.fbx(filepath=out_path + ".fbx")
                elif fmt == 'GLB':
                    bpy.ops.export_scene.gltf(filepath=out_path + ".glb", export_format='GLB')
                elif fmt == 'GLTF':
                    bpy.ops.export_scene.gltf(filepath=out_path + ".gltf", export_format='GLTF_SEPARATE')
                elif fmt == 'STL':
                    bpy.ops.wm.stl_export(filepath=out_path + ".stl")
                elif fmt == 'USD':
                    bpy.ops.wm.usd_export(filepath=out_path + ".usd")
                elif fmt == 'BLEND':
                    bpy.ops.wm.save_as_mainfile(filepath=out_path + ".blend")

                item.status = "Done"
            except Exception as e:
                item.status = f"Error: {e}"

        bp.progress = 100
        bp.status_text = "Conversion complete"
        self.report({'INFO'}, bp.status_text)
        return {'FINISHED'}


class RECA_OT_batch_rename_objects(Operator):
    """Rename objects in current scene"""
    bl_idname = "reca.batch_rename_objects"
    bl_label = "Batch Rename Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bp = context.scene.reca_batch_processor
        mode = bp.rename_mode
        count = 0

        if mode == 'BY_TYPE':
            counters = {}
            for obj in sorted(bpy.data.objects, key=lambda o: o.name):
                prefix = obj.type.lower()
                counters[prefix] = counters.get(prefix, 0) + 1
                obj.name = f"{prefix}_{counters[prefix]:03d}"
                count += 1
        elif mode == 'PREFIX':
            for obj in bpy.data.objects:
                obj.name = bp.rename_prefix + obj.name
                count += 1
        elif mode == 'SUFFIX':
            for obj in bpy.data.objects:
                obj.name = obj.name + bp.rename_suffix
                count += 1
        elif mode == 'LOWERCASE':
            for obj in bpy.data.objects:
                obj.name = obj.name.lower()
                count += 1
        elif mode == 'REPLACE':
            for obj in bpy.data.objects:
                if bp.rename_find in obj.name:
                    obj.name = obj.name.replace(bp.rename_find, bp.rename_replace)
                    count += 1

        self.report({'INFO'}, f"Renamed {count} objects")
        return {'FINISHED'}


class RECA_OT_batch_optimize(Operator):
    """Decimate all mesh objects in the scene"""
    bl_idname = "reca.batch_optimize"
    bl_label = "Optimize Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bp = context.scene.reca_batch_processor
        count = 0
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            mod = obj.modifiers.new(name="RECA_Decimate", type='DECIMATE')
            mod.ratio = bp.decimate_ratio
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=mod.name)
            count += 1
        self.report({'INFO'}, f"Optimized {count} meshes (ratio={bp.decimate_ratio:.2f})")
        return {'FINISHED'}


class RECA_OT_batch_purge(Operator):
    """Remove all orphan data blocks"""
    bl_idname = "reca.batch_purge"
    bl_label = "Purge Unused Data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed = 0
        for attr in ('meshes', 'materials', 'textures', 'images',
                      'node_groups', 'worlds', 'cameras', 'lights',
                      'curves', 'fonts', 'armatures', 'actions',
                      'particles', 'grease_pencils'):
            data = getattr(bpy.data, attr, None)
            if data is None:
                continue
            for block in list(data):
                if block.users == 0:
                    data.remove(block)
                    removed += 1
        self.report({'INFO'}, f"Purged {removed} orphan data blocks")
        return {'FINISHED'}


class RECA_OT_batch_scene_info(Operator):
    """Print scene statistics to console"""
    bl_idname = "reca.batch_scene_info"
    bl_label = "Scene Info"

    def execute(self, context):
        print("=" * 50)
        print("RECA Scene Statistics")
        print("=" * 50)
        print(f"Objects:     {len(bpy.data.objects)}")
        print(f"Meshes:      {len(bpy.data.meshes)}")
        print(f"Materials:   {len(bpy.data.materials)}")
        print(f"Images:      {len(bpy.data.images)}")
        print(f"Collections: {len(bpy.data.collections)}")
        total_verts = sum(len(m.vertices) for m in bpy.data.meshes)
        total_faces = sum(len(m.polygons) for m in bpy.data.meshes)
        print(f"Total verts: {total_verts:,}")
        print(f"Total faces: {total_faces:,}")
        print("-" * 50)
        for obj in bpy.data.objects:
            info = f"  {obj.name} ({obj.type})"
            if obj.type == 'MESH' and obj.data:
                info += f" — {len(obj.data.vertices)} verts, {len(obj.data.polygons)} faces"
            print(info)
        print("=" * 50)
        self.report({'INFO'}, f"Scene: {len(bpy.data.objects)} objects, {total_verts:,} verts")
        return {'FINISHED'}


class RECA_OT_batch_export_separated(Operator):
    """Export each object as a separate file"""
    bl_idname = "reca.batch_export_separated"
    bl_label = "Export Separated"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bp = context.scene.reca_batch_processor
        output = bpy.path.abspath(bp.output_dir)
        os.makedirs(output, exist_ok=True)
        fmt = bp.convert_format
        count = 0

        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            base = os.path.join(output, obj.name)

            try:
                if fmt == 'OBJ':
                    bpy.ops.wm.obj_export(filepath=base + ".obj", export_selected_objects=True)
                elif fmt == 'FBX':
                    bpy.ops.export_scene.fbx(filepath=base + ".fbx", use_selection=True)
                elif fmt in ('GLB', 'GLTF'):
                    bpy.ops.export_scene.gltf(filepath=base + ".glb",
                                              export_format='GLB', use_selection=True)
                elif fmt == 'STL':
                    bpy.ops.wm.stl_export(filepath=base + ".stl", export_selected_objects=True)
                count += 1
            except Exception as e:
                self.report({'WARNING'}, f"Failed: {obj.name}: {e}")

        self.report({'INFO'}, f"Exported {count} objects")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UI Draw
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    bp = context.scene.reca_batch_processor

    # File operations
    box = layout.box()
    box.label(text="Batch File Operations", icon='FILE_REFRESH')
    box.prop(bp, "source_dir")
    box.prop(bp, "output_dir")
    box.prop(bp, "file_pattern")
    box.operator("reca.batch_scan_files", icon='VIEWZOOM')

    if len(bp.files) > 0:
        box.label(text=f"{len(bp.files)} files found", icon='INFO')

    layout.separator()

    # Operation selector
    box = layout.box()
    box.label(text="Operation", icon='MODIFIER')
    box.prop(bp, "operation", text="")

    op = bp.operation
    if op == 'CONVERT':
        box.prop(bp, "convert_format")
        box.operator("reca.batch_convert", icon='EXPORT')

    elif op == 'RENAME_OBJ':
        box.prop(bp, "rename_mode")
        if bp.rename_mode == 'PREFIX':
            box.prop(bp, "rename_prefix")
        elif bp.rename_mode == 'SUFFIX':
            box.prop(bp, "rename_suffix")
        elif bp.rename_mode == 'REPLACE':
            box.prop(bp, "rename_find")
            box.prop(bp, "rename_replace")
        box.operator("reca.batch_rename_objects", icon='SORTALPHA')

    elif op == 'OPTIMIZE':
        box.prop(bp, "decimate_ratio", slider=True)
        box.operator("reca.batch_optimize", icon='MOD_DECIM')

    elif op == 'PURGE':
        box.operator("reca.batch_purge", icon='ORPHAN_DATA')

    elif op == 'INFO':
        box.operator("reca.batch_scene_info", icon='INFO')

    elif op == 'EXPORT_SEP':
        box.prop(bp, "convert_format")
        box.operator("reca.batch_export_separated", icon='EXPORT')

    elif op == 'RENDER':
        box.prop(bp, "render_engine")
        box.prop(bp, "render_samples")

    # Progress
    if bp.progress > 0:
        layout.separator()
        box = layout.box()
        box.prop(bp, "progress", text=bp.status_text)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_batch_file_item,
    RECA_PG_batch_processor,
    RECA_OT_batch_scan_files,
    RECA_OT_batch_convert,
    RECA_OT_batch_rename_objects,
    RECA_OT_batch_optimize,
    RECA_OT_batch_purge,
    RECA_OT_batch_scene_info,
    RECA_OT_batch_export_separated,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_batch_processor = PointerProperty(type=RECA_PG_batch_processor)


def unregister():
    del bpy.types.Scene.reca_batch_processor
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
