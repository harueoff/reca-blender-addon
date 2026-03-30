# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    IntProperty,
    FloatProperty,
)


class RECA_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    # ── General ──
    default_export_path: StringProperty(
        name="Default Export Path",
        subtype='DIR_PATH',
        default="//exports/",
    )
    default_import_path: StringProperty(
        name="Default Import Path",
        subtype='DIR_PATH',
        default="//",
    )

    # ── Render ──
    render_output_path: StringProperty(
        name="Render Output Path",
        subtype='DIR_PATH',
        default="//renders/",
    )
    render_open_after: BoolProperty(
        name="Open Folder After Render",
        default=True,
    )

    # ── Batch ──
    batch_backup: BoolProperty(
        name="Create Backups Before Batch Operations",
        default=True,
    )
    batch_max_threads: IntProperty(
        name="Max Background Processes",
        default=4,
        min=1,
        max=16,
    )

    # ── UI ──
    ui_show_tooltips: BoolProperty(
        name="Show Extended Tooltips",
        default=True,
    )
    ui_compact_mode: BoolProperty(
        name="Compact Mode",
        default=False,
    )
    ui_theme: EnumProperty(
        name="Panel Theme",
        items=[
            ('DEFAULT', "Default", "Use Blender theme"),
            ('DARK', "Dark Pro", "Darker panels"),
            ('ACCENT', "Accent", "Accent color highlights"),
        ],
        default='DEFAULT',
    )

    # ── Procedural ──
    proc_seed: IntProperty(
        name="Global Seed",
        default=42,
        min=0,
    )
    proc_quality: EnumProperty(
        name="Preview Quality",
        items=[
            ('LOW', "Low", "Fast preview"),
            ('MEDIUM', "Medium", "Balanced"),
            ('HIGH', "High", "Full quality"),
        ],
        default='MEDIUM',
    )

    def draw(self, context):
        layout = self.layout

        # General
        box = layout.box()
        box.label(text="General", icon='PREFERENCES')
        box.prop(self, "default_export_path")
        box.prop(self, "default_import_path")

        # Render
        box = layout.box()
        box.label(text="Render", icon='RENDER_STILL')
        box.prop(self, "render_output_path")
        box.prop(self, "render_open_after")

        # Batch
        box = layout.box()
        box.label(text="Batch Processing", icon='FILE_REFRESH')
        box.prop(self, "batch_backup")
        box.prop(self, "batch_max_threads")

        # Procedural
        box = layout.box()
        box.label(text="Procedural", icon='MOD_BUILD')
        box.prop(self, "proc_seed")
        box.prop(self, "proc_quality")

        # UI
        box = layout.box()
        box.label(text="Interface", icon='WINDOW')
        box.prop(self, "ui_show_tooltips")
        box.prop(self, "ui_compact_mode")
        box.prop(self, "ui_theme")


classes = [RECA_AddonPreferences]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
