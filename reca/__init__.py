# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 RECA Team

bl_info = {
    "name": "RECA - All-in-One 3D Toolkit",
    "author": "RECA Team",
    "version": (2, 0, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > RECA",
    "description": "Professional multi-purpose 3D toolkit: Scene Builder, Batch Processor, Procedural Generator, Quick Tools, Render Manager, Material Tools, MCP Server, AI Integration",
    "warning": "",
    "doc_url": "https://github.com/reca-addon/reca/wiki",
    "tracker_url": "https://github.com/reca-addon/reca/issues",
    "category": "3D View",
}

import bpy
from bpy.props import EnumProperty, PointerProperty

from . import preferences
from .modules import (
    scene_builder,
    batch_processor,
    procedural_gen,
    quick_tools,
    render_manager,
    material_tools,
    mcp_server,
    ai_integration,
)

modules = [
    preferences,
    scene_builder,
    batch_processor,
    procedural_gen,
    quick_tools,
    render_manager,
    material_tools,
    mcp_server,
    ai_integration,
]


# ─────────────────────────────────────────────
#  Main Panel (Tab Container)
# ─────────────────────────────────────────────

class RECA_PT_main(bpy.types.Panel):
    bl_label = "RECA Toolkit"
    bl_idname = "RECA_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "RECA"

    def draw(self, context):
        layout = self.layout
        props = context.scene.reca
        layout.prop(props, "active_tab", expand=True)


class RECA_PT_tab_content(bpy.types.Panel):
    bl_label = ""
    bl_idname = "RECA_PT_tab_content"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "RECA"
    bl_parent_id = "RECA_PT_main"
    bl_options = {'HIDE_HEADER'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.reca
        tab = props.active_tab

        if tab == 'SCENE':
            scene_builder.draw_panel(layout, context)
        elif tab == 'BATCH':
            batch_processor.draw_panel(layout, context)
        elif tab == 'PROCEDURAL':
            procedural_gen.draw_panel(layout, context)
        elif tab == 'TOOLS':
            quick_tools.draw_panel(layout, context)
        elif tab == 'RENDER':
            render_manager.draw_panel(layout, context)
        elif tab == 'MATERIAL':
            material_tools.draw_panel(layout, context)
        elif tab == 'MCP':
            mcp_server.draw_panel(layout, context)
        elif tab == 'AI':
            ai_integration.draw_panel(layout, context)


# ─────────────────────────────────────────────
#  Scene Properties
# ─────────────────────────────────────────────

class RECA_SceneProperties(bpy.types.PropertyGroup):
    active_tab: EnumProperty(
        name="Tab",
        items=[
            ('SCENE', "Scene", "Scene Builder", 'SCENE_DATA', 0),
            ('BATCH', "Batch", "Batch Processor", 'FILE_REFRESH', 1),
            ('PROCEDURAL', "Proc", "Procedural Generator", 'MOD_BUILD', 2),
            ('TOOLS', "Tools", "Quick Tools", 'TOOL_SETTINGS', 3),
            ('RENDER', "Render", "Render Manager", 'RENDER_STILL', 4),
            ('MATERIAL', "Mat", "Material Tools", 'MATERIAL', 5),
            ('MCP', "MCP", "MCP Server for AI Control", 'LINKED', 6),
            ('AI', "AI", "AI Integration", 'LIGHT_SUN', 7),
        ],
        default='SCENE',
    )


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_SceneProperties,
    RECA_PT_main,
    RECA_PT_tab_content,
]


def register():
    for mod in modules:
        mod.register()
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca = PointerProperty(type=RECA_SceneProperties)


def unregister():
    del bpy.types.Scene.reca
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    for mod in reversed(modules):
        mod.unregister()


if __name__ == "__main__":
    register()
