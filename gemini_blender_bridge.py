#!/usr/bin/env python3
"""Gemini → RECA Blender MCP Bridge

Connects Google Gemini AI to RECA addon's MCP server,
allowing Gemini to control Blender via natural language.

Usage:
    pip install google-genai
    export GEMINI_API_KEY="your-api-key"
    python gemini_blender_bridge.py

    # Or with arguments:
    python gemini_blender_bridge.py --port 9877 --model gemini-2.5-flash

Prerequisites:
    1. RECA addon installed and MCP server started in Blender
    2. Google AI API key from https://aistudio.google.com/apikey
    3. pip install google-genai
"""

import json
import sys
import os
import urllib.request
import urllib.error
import argparse
from typing import Any

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai not installed.")
    print("Run: pip install google-genai")
    sys.exit(1)


# ─────────────────────────────────────────────
#  RECA MCP HTTP Client
# ─────────────────────────────────────────────

class RECAMCPClient:
    """Client for RECA addon's HTTP MCP server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9877):
        self.base_url = f"http://{host}:{port}"
        self._tools_cache = None

    def health(self) -> dict:
        return self._get("/health")

    def get_tools(self) -> list[dict]:
        if self._tools_cache is None:
            resp = self._post({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            })
            self._tools_cache = resp.get("result", {}).get("tools", [])
        return self._tools_cache

    def call_tool(self, name: str, arguments: dict) -> dict:
        resp = self._post({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        result = resp.get("result", {})
        content = result.get("content", [])
        if content:
            text = content[0].get("text", "{}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
        return result

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.base_url}{path}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _post(self, data: dict) -> dict:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())


# ─────────────────────────────────────────────
#  Build Gemini Function Declarations from MCP
# ─────────────────────────────────────────────

def mcp_schema_to_gemini_type(type_str: str) -> str:
    """Map MCP/JSON Schema types to Gemini types."""
    mapping = {
        "string": "STRING",
        "number": "NUMBER",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
        "array": "ARRAY",
        "object": "OBJECT",
    }
    return mapping.get(type_str, "STRING")


def build_gemini_tools(mcp_tools: list[dict]) -> list[types.Tool]:
    """Convert MCP tool schemas to Gemini function declarations."""
    declarations = []

    for tool in mcp_tools:
        properties = {}
        required = tool.get("inputSchema", {}).get("required", [])

        for pname, pspec in tool.get("inputSchema", {}).get("properties", {}).items():
            prop = {
                "type": mcp_schema_to_gemini_type(pspec.get("type", "string")),
            }
            if "description" in pspec and pspec["description"]:
                prop["description"] = pspec["description"]
            properties[pname] = prop

        decl = types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    k: types.Schema(**v) for k, v in properties.items()
                },
                required=required if required else None,
            ) if properties else None,
        )
        declarations.append(decl)

    return [types.Tool(function_declarations=declarations)]


# ─────────────────────────────────────────────
#  Gemini ↔ Blender Chat Loop
# ─────────────────────────────────────────────

SYSTEM_INSTRUCTION = """You are a 3D artist assistant controlling Blender through the RECA addon.
You have access to tools that manipulate the Blender scene.

When the user asks you to create, modify, or arrange 3D objects:
1. Use the available tools to execute the actions
2. Describe what you did after each action
3. For complex scenes, break down into multiple tool calls

Tips:
- Use setup_scene for quick lighting/camera/environment setup
- Use add_object to create primitives, set_material for colors
- Use transform_object to position/rotate/scale objects
- Use generate_procedural for complex geometry (buildings, terrain, trees)
- Locations are [x, y, z], rotations in degrees, colors in [r, g, b] 0-1 range
- Use execute_python for anything not covered by existing tools

Always respond in the same language as the user."""


def run_chat(mcp_client: RECAMCPClient, model_name: str, api_key: str = None):
    """Run interactive chat between user → Gemini → Blender."""

    # Init Gemini
    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    gemini = genai.Client(**client_kwargs)

    # Fetch MCP tools and convert to Gemini format
    print("Connecting to RECA MCP server...")
    try:
        health = mcp_client.health()
        print(f"  Server: {health.get('server')} v{health.get('version', '?')}")
    except Exception as e:
        print(f"  ERROR: Cannot connect to RECA MCP server: {e}")
        print(f"  Make sure Blender is running with RECA addon and MCP server started.")
        sys.exit(1)

    mcp_tools = mcp_client.get_tools()
    gemini_tools = build_gemini_tools(mcp_tools)
    print(f"  Loaded {len(mcp_tools)} tools from RECA")

    # Create chat
    chat = gemini.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=gemini_tools,
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.AUTO,
                )
            ),
            temperature=0.7,
        ),
    )

    tool_names = [t["name"] for t in mcp_tools]
    print(f"\n  Tools: {', '.join(tool_names[:8])}{'...' if len(tool_names) > 8 else ''}")
    print(f"  Model: {model_name}")
    print("\n" + "=" * 60)
    print("  Gemini ↔ Blender Bridge Ready!")
    print("  Type your request (or 'quit' to exit)")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("\033[96mYou:\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        try:
            response = chat.send_message(user_input)

            # Handle function calls in a loop
            while response.function_calls:
                function_responses = []

                for fc in response.function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    print(f"\033[93m  [Tool] {tool_name}({json.dumps(tool_args, ensure_ascii=False)})\033[0m")

                    try:
                        result = mcp_client.call_tool(tool_name, tool_args)
                        result_str = json.dumps(result, ensure_ascii=False)
                        print(f"\033[92m  [Result] {result_str[:200]}{'...' if len(result_str) > 200 else ''}\033[0m")
                    except Exception as e:
                        result = {"error": str(e)}
                        print(f"\033[91m  [Error] {e}\033[0m")

                    function_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response=result,
                        )
                    )

                # Send tool results back to Gemini
                response = chat.send_message(function_responses)

            # Print final text response
            if response.text:
                print(f"\n\033[97mGemini:\033[0m {response.text}\n")

        except Exception as e:
            print(f"\033[91mError: {e}\033[0m\n")


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gemini → RECA Blender MCP Bridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gemini_blender_bridge.py
  python gemini_blender_bridge.py --model gemini-2.5-pro
  python gemini_blender_bridge.py --port 9877 --api-key YOUR_KEY

Environment variables:
  GEMINI_API_KEY or GOOGLE_API_KEY  — Google AI API key
        """,
    )
    parser.add_argument("--host", default="127.0.0.1", help="RECA MCP server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9877, help="RECA MCP HTTP port (default: 9877)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model (default: gemini-2.5-flash)")
    parser.add_argument("--api-key", default=None, help="Google AI API key (or use GEMINI_API_KEY env var)")
    args = parser.parse_args()

    mcp_client = RECAMCPClient(args.host, args.port)
    run_chat(mcp_client, args.model, args.api_key)


if __name__ == "__main__":
    main()
