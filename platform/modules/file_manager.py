"""
Janovum Module — File Manager
Manages client files — upload, download, organize, search.
Each client gets their own folder.

How it works:
  1. Client sends a file via Telegram/WhatsApp or uploads via dashboard
  2. Python stores it in the client's folder
  3. Claude can read, search, and organize files
  4. Files accessible from any module that needs them
"""

import json
import os
import sys
import shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_NAME = "file_manager"
MODULE_DESC = "File Manager — upload, organize, search client files"

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clients")


def get_client_dir(client_id):
    """Get or create a client's file directory."""
    path = os.path.join(BASE_DIR, client_id, "files")
    os.makedirs(path, exist_ok=True)
    return path


def save_file(client_id, filename, content_bytes):
    """Save a file to the client's directory."""
    client_dir = get_client_dir(client_id)
    filepath = os.path.join(client_dir, filename)

    # Don't overwrite — add timestamp if exists
    if os.path.exists(filepath):
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(client_dir, f"{name}_{timestamp}{ext}")

    with open(filepath, "wb") as f:
        f.write(content_bytes)

    return {
        "saved": True,
        "path": filepath,
        "size": len(content_bytes),
        "filename": os.path.basename(filepath)
    }


def list_files(client_id, subfolder=None):
    """List all files in a client's directory."""
    client_dir = get_client_dir(client_id)
    if subfolder:
        client_dir = os.path.join(client_dir, subfolder)

    if not os.path.exists(client_dir):
        return {"files": [], "count": 0}

    files = []
    for item in os.listdir(client_dir):
        full_path = os.path.join(client_dir, item)
        stat = os.stat(full_path)
        files.append({
            "name": item,
            "is_dir": os.path.isdir(full_path),
            "size": stat.st_size if not os.path.isdir(full_path) else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files, "count": len(files)}


def read_file(client_id, filename):
    """Read a text file from client's directory."""
    client_dir = get_client_dir(client_id)
    filepath = os.path.join(client_dir, filename)

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filename}"}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filename": filename, "content": content[:50000], "size": len(content)}
    except UnicodeDecodeError:
        return {"filename": filename, "content": "[Binary file — cannot display as text]",
                "size": os.path.getsize(filepath)}


def delete_file(client_id, filename):
    """Delete a file from client's directory."""
    client_dir = get_client_dir(client_id)
    filepath = os.path.join(client_dir, filename)

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filename}"}

    if os.path.isdir(filepath):
        shutil.rmtree(filepath)
    else:
        os.remove(filepath)

    return {"deleted": True, "filename": filename}


def search_files(client_id, query):
    """Search files by name in client's directory."""
    client_dir = get_client_dir(client_id)
    results = []

    for root, dirs, files in os.walk(client_dir):
        for f in files:
            if query.lower() in f.lower():
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, client_dir)
                results.append({
                    "name": f,
                    "path": rel_path,
                    "size": os.path.getsize(full_path)
                })

    return {"query": query, "results": results, "count": len(results)}


def create_folder(client_id, folder_name):
    """Create a subfolder in client's directory."""
    client_dir = get_client_dir(client_id)
    folder_path = os.path.join(client_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return {"created": True, "folder": folder_name}


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "file_list",
        "description": "List files in the client's storage",
        "input_schema": {
            "type": "object",
            "properties": {
                "subfolder": {"type": "string", "description": "Optional subfolder to list"}
            }
        }
    },
    {
        "name": "file_read",
        "description": "Read a text file from storage",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name of the file to read"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "file_search",
        "description": "Search files by name",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "file_delete",
        "description": "Delete a file from storage",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name of the file to delete"}
            },
            "required": ["filename"]
        }
    }
]


def execute_tool(tool_name, tool_input, client_id="default"):
    if tool_name == "file_list":
        return json.dumps(list_files(client_id, tool_input.get("subfolder")))
    elif tool_name == "file_read":
        return json.dumps(read_file(client_id, tool_input["filename"]))
    elif tool_name == "file_search":
        return json.dumps(search_files(client_id, tool_input["query"]))
    elif tool_name == "file_delete":
        return json.dumps(delete_file(client_id, tool_input["filename"]))
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
