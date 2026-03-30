# SPDX-License-Identifier: GPL-3.0-or-later
"""RECA AI Integration — connect to OpenClaw.ai, Google Antigravity,
and other AI services for intelligent 3D workflow assistance.

Features:
  - AI-powered text-to-3D scene generation via natural language
  - Smart material suggestion based on object context
  - AI-assisted camera placement
  - Integration with OpenClaw.ai API
  - Integration with Google Antigravity API
  - Local prompt history and favorites
"""

import bpy
import json
import os
import threading
from bpy.types import Operator, PropertyGroup, UIList
from bpy.props import (
    EnumProperty,
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    CollectionProperty,
    PointerProperty,
)


# ─────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────

class RECA_PG_ai_prompt_item(PropertyGroup):
    text: StringProperty(name="Prompt")
    result: StringProperty(name="Result")
    timestamp: StringProperty(name="Time")
    favorite: BoolProperty(name="Favorite", default=False)


class RECA_PG_ai_integration(PropertyGroup):
    # Provider
    provider: EnumProperty(
        name="AI Provider",
        items=[
            ('OPENCLAW', "OpenClaw.ai", "OpenClaw AI agent platform"),
            ('GOOGLE_ANTIGRAVITY', "Google Antigravity", "Google's 3D AI service"),
            ('ANTHROPIC', "Anthropic Claude", "Claude API"),
            ('OPENAI', "OpenAI", "GPT API"),
            ('LOCAL', "Local / Ollama", "Local LLM via Ollama"),
            ('CUSTOM', "Custom API", "Custom REST API endpoint"),
        ],
        default='OPENCLAW',
    )

    # API Keys (stored in addon prefs, displayed masked)
    openclaw_api_key: StringProperty(
        name="OpenClaw API Key",
        subtype='PASSWORD',
    )
    google_api_key: StringProperty(
        name="Google API Key",
        subtype='PASSWORD',
    )
    anthropic_api_key: StringProperty(
        name="Anthropic API Key",
        subtype='PASSWORD',
    )
    openai_api_key: StringProperty(
        name="OpenAI API Key",
        subtype='PASSWORD',
    )
    custom_endpoint: StringProperty(
        name="Custom Endpoint",
        default="http://localhost:11434/api/generate",
    )
    custom_model: StringProperty(
        name="Model",
        default="llama3",
    )

    # Prompt
    prompt: StringProperty(
        name="Prompt",
        description="Describe what you want to create or modify",
        default="",
    )
    system_context: EnumProperty(
        name="Context",
        items=[
            ('SCENE', "Scene Generation", "Create or modify the entire scene"),
            ('MATERIAL', "Material", "Create or suggest materials"),
            ('MODELING', "Modeling", "Create or modify 3D objects"),
            ('LIGHTING', "Lighting", "Set up or adjust lighting"),
            ('ANIMATION', "Animation", "Create keyframe animations"),
            ('CAMERA', "Camera", "Camera setup and placement"),
            ('SCRIPT', "Python Script", "Generate Blender Python script"),
        ],
        default='SCENE',
    )

    # Options
    auto_execute: BoolProperty(
        name="Auto Execute",
        description="Automatically execute generated Python code",
        default=False,
    )
    include_scene_context: BoolProperty(
        name="Include Scene Context",
        description="Send current scene info to AI for better results",
        default=True,
    )
    temperature: FloatProperty(
        name="Temperature",
        description="AI creativity level (0=precise, 1=creative)",
        default=0.7,
        min=0.0,
        max=2.0,
    )
    max_tokens: IntProperty(
        name="Max Tokens",
        default=2048,
        min=256,
        max=8192,
    )

    # Status
    status: StringProperty(name="Status", default="Ready")
    last_response: StringProperty(name="Last Response", default="")
    is_processing: BoolProperty(name="Processing", default=False)

    # History
    history: CollectionProperty(type=RECA_PG_ai_prompt_item)
    history_index: IntProperty(default=0)


# ─────────────────────────────────────────────
#  API Clients
# ─────────────────────────────────────────────

def _get_scene_context():
    """Build a context string describing the current scene."""
    from ..utils import scene_stats
    stats = scene_stats()
    objects = []
    for obj in bpy.data.objects:
        info = f"- {obj.name} ({obj.type}) at {list(obj.location)}"
        if obj.type == 'MESH' and obj.data:
            info += f" [{len(obj.data.vertices)} verts]"
        objects.append(info)

    context = f"""Current Blender Scene:
Objects: {stats['objects']}, Meshes: {stats['meshes']}, Materials: {stats['materials']}
Total vertices: {stats['total_vertices']:,}, Total faces: {stats['total_faces']:,}

Objects in scene:
{chr(10).join(objects[:50])}
"""
    return context


SYSTEM_PROMPTS = {
    'SCENE': """You are a Blender Python expert. Generate bpy Python code to create or modify 3D scenes.
Always use bpy.ops and bpy.data. Return ONLY valid Python code, no explanations.
Wrap the code in a function called reca_execute() and call it at the end.""",

    'MATERIAL': """You are a Blender material expert. Generate bpy Python code to create PBR materials.
Use Principled BSDF shader nodes. Return ONLY valid Python code.
Wrap the code in a function called reca_execute() and call it at the end.""",

    'MODELING': """You are a Blender modeling expert. Generate bpy Python code to create 3D objects.
Use bmesh for complex geometry when needed. Return ONLY valid Python code.
Wrap the code in a function called reca_execute() and call it at the end.""",

    'LIGHTING': """You are a Blender lighting expert. Generate bpy Python code for professional lighting.
Return ONLY valid Python code. Wrap in reca_execute() function.""",

    'ANIMATION': """You are a Blender animation expert. Generate bpy Python code for keyframe animation.
Return ONLY valid Python code. Wrap in reca_execute() function.""",

    'CAMERA': """You are a Blender camera expert. Generate bpy Python code for camera setup.
Return ONLY valid Python code. Wrap in reca_execute() function.""",

    'SCRIPT': """You are a Blender Python scripting expert. Generate any bpy Python code the user requests.
Return ONLY valid Python code. Wrap in reca_execute() function.""",
}


def _call_api_openclaw(ai_props, full_prompt):
    """Call OpenClaw.ai API."""
    import urllib.request
    url = "https://api.openclaw.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ai_props.openclaw_api_key}",
    }
    payload = {
        "model": "openclaw-3d",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPTS.get(ai_props.system_context, SYSTEM_PROMPTS['SCRIPT'])},
            {"role": "user", "content": full_prompt},
        ],
        "temperature": ai_props.temperature,
        "max_tokens": ai_props.max_tokens,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


def _call_api_google(ai_props, full_prompt):
    """Call Google Antigravity API."""
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={ai_props.google_api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [
                {"text": SYSTEM_PROMPTS.get(ai_props.system_context, SYSTEM_PROMPTS['SCRIPT'])},
                {"text": full_prompt},
            ]
        }],
        "generationConfig": {
            "temperature": ai_props.temperature,
            "maxOutputTokens": ai_props.max_tokens,
        },
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]


def _call_api_anthropic(ai_props, full_prompt):
    """Call Anthropic Claude API."""
    import urllib.request
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ai_props.anthropic_api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": ai_props.max_tokens,
        "system": SYSTEM_PROMPTS.get(ai_props.system_context, SYSTEM_PROMPTS['SCRIPT']),
        "messages": [{"role": "user", "content": full_prompt}],
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["content"][0]["text"]


def _call_api_openai(ai_props, full_prompt):
    """Call OpenAI API."""
    import urllib.request
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ai_props.openai_api_key}",
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPTS.get(ai_props.system_context, SYSTEM_PROMPTS['SCRIPT'])},
            {"role": "user", "content": full_prompt},
        ],
        "temperature": ai_props.temperature,
        "max_tokens": ai_props.max_tokens,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


def _call_api_local(ai_props, full_prompt):
    """Call local Ollama API."""
    import urllib.request
    url = ai_props.custom_endpoint
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": ai_props.custom_model,
        "prompt": SYSTEM_PROMPTS.get(ai_props.system_context, "") + "\n\n" + full_prompt,
        "stream": False,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result.get("response", result.get("text", str(result)))


API_CLIENTS = {
    'OPENCLAW': _call_api_openclaw,
    'GOOGLE_ANTIGRAVITY': _call_api_google,
    'ANTHROPIC': _call_api_anthropic,
    'OPENAI': _call_api_openai,
    'LOCAL': _call_api_local,
    'CUSTOM': _call_api_local,
}


# ─────────────────────────────────────────────
#  Code extraction
# ─────────────────────────────────────────────

def _extract_python_code(text):
    """Extract Python code from AI response (handles markdown blocks)."""
    # Try to find ```python ... ``` blocks
    if "```python" in text:
        blocks = text.split("```python")
        if len(blocks) > 1:
            code = blocks[1].split("```")[0]
            return code.strip()
    if "```" in text:
        blocks = text.split("```")
        if len(blocks) > 2:
            code = blocks[1]
            if code.startswith("python\n"):
                code = code[7:]
            return code.strip()
    # Assume entire response is code
    return text.strip()


# ─────────────────────────────────────────────
#  Operators
# ─────────────────────────────────────────────

class RECA_OT_ai_send_prompt(Operator):
    """Send prompt to AI provider and get Blender Python code"""
    bl_idname = "reca.ai_send_prompt"
    bl_label = "Send to AI"

    def execute(self, context):
        ai = context.scene.reca_ai
        if not ai.prompt.strip():
            self.report({'WARNING'}, "Enter a prompt first")
            return {'CANCELLED'}

        ai.is_processing = True
        ai.status = "Sending..."

        # Build full prompt
        full_prompt = ai.prompt
        if ai.include_scene_context:
            full_prompt = _get_scene_context() + "\n\nUser request: " + ai.prompt

        # Run in background thread
        def _worker():
            try:
                client = API_CLIENTS.get(ai.provider)
                if client is None:
                    ai.status = f"Unknown provider: {ai.provider}"
                    ai.is_processing = False
                    return

                response = client(ai, full_prompt)
                ai.last_response = response
                ai.status = "Response received"

                # Save to history
                import datetime
                item = ai.history.add()
                item.text = ai.prompt
                item.result = response[:500]
                item.timestamp = datetime.datetime.now().strftime("%H:%M:%S")

                # Auto-execute if enabled
                if ai.auto_execute:
                    code = _extract_python_code(response)
                    bpy.app.timers.register(lambda: _execute_on_main(code), first_interval=0.1)

            except Exception as e:
                ai.status = f"Error: {str(e)[:50]}"
                ai.last_response = str(e)
            finally:
                ai.is_processing = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        self.report({'INFO'}, "Prompt sent to AI")
        return {'FINISHED'}


def _execute_on_main(code):
    """Execute code on the main thread via timer."""
    try:
        exec(code, {"bpy": bpy, "mathutils": __import__('mathutils'), "__builtins__": __builtins__})
    except Exception as e:
        print(f"RECA AI execution error: {e}")
    return None  # Don't repeat


class RECA_OT_ai_execute_response(Operator):
    """Execute the Python code from the last AI response"""
    bl_idname = "reca.ai_execute_response"
    bl_label = "Execute Code"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ai = context.scene.reca_ai
        if not ai.last_response:
            self.report({'WARNING'}, "No AI response to execute")
            return {'CANCELLED'}

        code = _extract_python_code(ai.last_response)
        try:
            exec(code, {"bpy": bpy, "mathutils": __import__('mathutils'), "__builtins__": __builtins__})
            self.report({'INFO'}, "Code executed successfully")
        except Exception as e:
            self.report({'ERROR'}, f"Execution error: {e}")
        return {'FINISHED'}


class RECA_OT_ai_copy_response(Operator):
    """Copy the last AI response to clipboard"""
    bl_idname = "reca.ai_copy_response"
    bl_label = "Copy Response"

    def execute(self, context):
        ai = context.scene.reca_ai
        if ai.last_response:
            context.window_manager.clipboard = ai.last_response
            self.report({'INFO'}, "Response copied to clipboard")
        return {'FINISHED'}


class RECA_OT_ai_clear_history(Operator):
    """Clear prompt history"""
    bl_idname = "reca.ai_clear_history"
    bl_label = "Clear History"

    def execute(self, context):
        context.scene.reca_ai.history.clear()
        self.report({'INFO'}, "History cleared")
        return {'FINISHED'}


class RECA_OT_ai_use_history(Operator):
    """Load a prompt from history"""
    bl_idname = "reca.ai_use_history"
    bl_label = "Use Prompt"

    index: IntProperty()

    def execute(self, context):
        ai = context.scene.reca_ai
        if 0 <= self.index < len(ai.history):
            ai.prompt = ai.history[self.index].text
        return {'FINISHED'}


# Quick prompts
QUICK_PROMPTS = {
    'PRODUCT_SCENE': "Create a professional product photography scene with a turntable, 3-point lighting, and a gradient background",
    'LOW_POLY_LANDSCAPE': "Create a low-poly landscape with mountains, trees, and a river",
    'ROOM_INTERIOR': "Create a simple room interior with walls, floor, a window, a table, and two chairs",
    'SPACE_SCENE': "Create a space scene with a planet, asteroid belt, and volumetric lighting",
    'CHARACTER_POSE': "Set up a T-pose reference scene with front, side, and back cameras for character modeling",
    'ARCH_VIZ': "Create an architectural visualization exterior with a modern building, pathway, and landscaping",
}


class RECA_OT_ai_quick_prompt(Operator):
    """Use a quick preset prompt"""
    bl_idname = "reca.ai_quick_prompt"
    bl_label = "Quick Prompt"

    prompt_key: StringProperty()

    def execute(self, context):
        ai = context.scene.reca_ai
        ai.prompt = QUICK_PROMPTS.get(self.prompt_key, "")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  UIList for history
# ─────────────────────────────────────────────

class RECA_UL_ai_history(UIList):
    bl_idname = "RECA_UL_ai_history"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.label(text=item.timestamp, icon='TIME')
        row.label(text=item.text[:40])
        op = row.operator("reca.ai_use_history", text="", icon='LOOP_BACK')
        op.index = index


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

def draw_panel(layout, context):
    ai = context.scene.reca_ai

    # Provider
    box = layout.box()
    box.label(text="AI Assistant", icon='GHOST_ENABLED')
    box.prop(ai, "provider")

    # API Key
    provider = ai.provider
    if provider == 'OPENCLAW':
        box.prop(ai, "openclaw_api_key")
    elif provider == 'GOOGLE_ANTIGRAVITY':
        box.prop(ai, "google_api_key")
    elif provider == 'ANTHROPIC':
        box.prop(ai, "anthropic_api_key")
    elif provider == 'OPENAI':
        box.prop(ai, "openai_api_key")
    elif provider in ('LOCAL', 'CUSTOM'):
        box.prop(ai, "custom_endpoint")
        box.prop(ai, "custom_model")

    # Prompt
    layout.separator()
    box = layout.box()
    box.label(text="Prompt", icon='TEXT')
    box.prop(ai, "system_context")
    box.prop(ai, "prompt", text="")

    # Quick prompts
    row = box.row(align=True)
    row.label(text="Quick:", icon='PRESET')
    for key, label in [
        ('PRODUCT_SCENE', "Product"),
        ('LOW_POLY_LANDSCAPE', "Landscape"),
        ('ROOM_INTERIOR', "Room"),
    ]:
        op = row.operator("reca.ai_quick_prompt", text=label)
        op.prompt_key = key

    row = box.row(align=True)
    for key, label in [
        ('SPACE_SCENE', "Space"),
        ('CHARACTER_POSE', "Char Ref"),
        ('ARCH_VIZ', "Arch Viz"),
    ]:
        op = row.operator("reca.ai_quick_prompt", text=label)
        op.prompt_key = key

    # Options
    row = box.row(align=True)
    row.prop(ai, "include_scene_context", toggle=True, icon='SCENE_DATA')
    row.prop(ai, "auto_execute", toggle=True, icon='PLAY')

    col = box.column(align=True)
    col.prop(ai, "temperature", slider=True)
    col.prop(ai, "max_tokens")

    # Send button
    row = box.row()
    row.scale_y = 1.5
    if ai.is_processing:
        row.label(text=ai.status, icon='SORTTIME')
    else:
        row.operator("reca.ai_send_prompt", icon='EXPORT')

    # Response
    if ai.last_response:
        layout.separator()
        box = layout.box()
        box.label(text="Response", icon='IMPORT')

        # Show truncated response
        lines = ai.last_response.split('\n')[:10]
        for line in lines:
            box.label(text=line[:80])
        if len(ai.last_response.split('\n')) > 10:
            box.label(text="... (truncated)")

        row = box.row(align=True)
        row.operator("reca.ai_execute_response", icon='PLAY', text="Execute")
        row.operator("reca.ai_copy_response", icon='COPYDOWN', text="Copy")

    # History
    if len(ai.history) > 0:
        layout.separator()
        box = layout.box()
        row = box.row()
        row.label(text="History", icon='TIME')
        row.operator("reca.ai_clear_history", text="", icon='TRASH')
        box.template_list("RECA_UL_ai_history", "", ai, "history", ai, "history_index", rows=3)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

classes = [
    RECA_PG_ai_prompt_item,
    RECA_PG_ai_integration,
    RECA_UL_ai_history,
    RECA_OT_ai_send_prompt,
    RECA_OT_ai_execute_response,
    RECA_OT_ai_copy_response,
    RECA_OT_ai_clear_history,
    RECA_OT_ai_use_history,
    RECA_OT_ai_quick_prompt,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.reca_ai = PointerProperty(type=RECA_PG_ai_integration)


def unregister():
    del bpy.types.Scene.reca_ai
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
