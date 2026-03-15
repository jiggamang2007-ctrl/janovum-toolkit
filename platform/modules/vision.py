"""
Janovum Module — Vision / Image Analysis
Client sends a photo → Claude analyzes it.
Uses Claude's built-in vision capability.

How it works:
  1. Client sends image via Telegram or uploads via dashboard
  2. Python encodes image to base64
  3. Sends to Claude API with vision enabled
  4. Claude describes/analyzes the image
  5. Result sent back to client
"""

import base64
import json
import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import call_claude

MODULE_NAME = "vision"
MODULE_DESC = "Vision — send a photo, Claude analyzes it"


def analyze_image_file(image_path, prompt="Describe this image in detail.", client_context=""):
    """Analyze an image file using Claude's vision."""
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}"}

    ext = os.path.splitext(image_path)[1].lower()
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                   ".gif": "image/gif", ".webp": "image/webp"}
    media_type = media_types.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    return analyze_image_base64(image_data, media_type, prompt, client_context)


def analyze_image_url(image_url, prompt="Describe this image in detail.", client_context=""):
    """Download and analyze an image from a URL."""
    try:
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
        image_data = base64.b64encode(resp.content).decode("utf-8")

        content_type = resp.headers.get("content-type", "image/jpeg")
        if "png" in content_type:
            media_type = "image/png"
        elif "gif" in content_type:
            media_type = "image/gif"
        elif "webp" in content_type:
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"

        return analyze_image_base64(image_data, media_type, prompt, client_context)
    except Exception as e:
        return {"error": f"Failed to download image: {str(e)}"}


def analyze_image_base64(image_data, media_type, prompt="Describe this image.", client_context=""):
    """Analyze a base64-encoded image using Claude vision."""
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data
                }
            },
            {
                "type": "text",
                "text": prompt
            }
        ]
    }]

    system_prompt = "You are a visual analysis assistant for Janovum."
    if client_context:
        system_prompt += f"\nClient context: {client_context}"

    result = call_claude(messages, system_prompt=system_prompt)

    if "error" in result:
        return result
    return {"analysis": result.get("text", ""), "model_used": result.get("model_used", "")}


TOOLS = [
    {
        "name": "analyze_image",
        "description": "Analyze an image file or URL using Claude vision",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Local file path to the image"},
                "image_url": {"type": "string", "description": "URL of the image"},
                "prompt": {"type": "string", "description": "What to analyze about the image", "default": "Describe this image in detail."}
            }
        }
    }
]


def execute_tool(tool_name, tool_input):
    if tool_name == "analyze_image":
        prompt = tool_input.get("prompt", "Describe this image in detail.")
        if tool_input.get("image_path"):
            return json.dumps(analyze_image_file(tool_input["image_path"], prompt))
        elif tool_input.get("image_url"):
            return json.dumps(analyze_image_url(tool_input["image_url"], prompt))
        return json.dumps({"error": "Provide image_path or image_url"})
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
