"""Central Tool Registry for Open LLM DeskAgent."""

from __future__ import annotations

import asyncio
import json
from typing import Callable, Any, Dict, List, Coroutine


class ToolDef:
    def __init__(self, name: str, fn: Callable[..., Any], schema: dict):
        self.name = name
        self.fn = fn
        self.schema = schema


TOOL_REGISTRY: Dict[str, ToolDef] = {}


def register_tool(name: str, fn: Callable[..., Any], schema: dict) -> None:
    """Register a tool in the registry."""
    TOOL_REGISTRY[name] = ToolDef(name=name, fn=fn, schema=schema)


def get_all_schemas() -> List[dict]:
    """Get all tool schemas registered."""
    return [tool.schema for tool in TOOL_REGISTRY.values()]


async def dispatch_tool(name: str, args: dict, mcp_manager: Any = None) -> dict:
    """Execute a registered tool by name with arguments."""
    # 1. MCP Tools
    if name.startswith("mcp__"):
        if mcp_manager:
            return await mcp_manager.call_tool(name, args)
        else:
            return {"success": False, "error": "MCP Manager chưa được khởi tạo."}

    # 2. Plugin Tools
    from plugins.plugin_manager import PluginManager
    plugin_mgr = PluginManager()
    if name in plugin_mgr.tools_registry:
        res = await plugin_mgr.execute_tool(name, args)
        if isinstance(res, dict):
            return res
        return {"success": True, "output": res}

    # 3. System Registered Tools
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"success": False, "error": f"Không tìm thấy công cụ '{name}'."}

    try:
        if asyncio.iscoroutinefunction(tool.fn):
            return await tool.fn(**args)
        else:
            # Run blocking system tools in a separate thread if needed
            return tool.fn(**args)
    except Exception as e:
        import logging
        logging.error(f"Error executing tool '{name}': {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# WRAPPER FUNCTIONS (To sanitize arguments and handle defaults)
# ─────────────────────────────────────────────────────────────────────────────

def _wrap_execute_command(command: str) -> dict:
    from tools.computer_control import execute_command
    return execute_command(command.strip())


def _wrap_write_to_file(path: str, content: str, overwrite: bool = True) -> dict:
    from tools.file_writer import write_to_file
    return write_to_file(path, content, overwrite)


def _wrap_read_file(path: str) -> dict:
    from tools.file_reader import read_file
    return read_file(path)


def _wrap_mouse_click(x: int | str, y: int | str, button: str = "left", double_click: bool = False) -> dict:
    from tools.computer_control import mouse_click
    return mouse_click(int(x), int(y), button, double_click)


def _wrap_mouse_move(x: int | str, y: int | str) -> dict:
    from tools.computer_control import mouse_move
    return mouse_move(int(x), int(y))


def _wrap_mouse_scroll(clicks: int | str = 1, direction: str = "down", x: int | str | None = None, y: int | str | None = None) -> dict:
    from tools.computer_control import mouse_scroll
    x_val = int(x) if x is not None and str(x).strip() else None
    y_val = int(y) if y is not None and str(y).strip() else None
    return mouse_scroll(int(clicks), direction, x_val, y_val)


def _wrap_mouse_drag(x: int | str, y: int | str, button: str = "left", duration: float | str = 0.5) -> dict:
    from tools.computer_control import mouse_drag
    return mouse_drag(int(x), int(y), button, float(duration))


def _wrap_keyboard_type(text: str) -> dict:
    from tools.computer_control import keyboard_type
    return keyboard_type(text)


def _wrap_keyboard_press(keys: str) -> dict:
    from tools.computer_control import keyboard_press
    return keyboard_press(keys)


async def _wrap_open_application(app_name: str) -> dict:
    from agents.desktop.desktop_agent import DesktopAgent
    agent = DesktopAgent()
    return await agent.open_application(app_name)


def _wrap_open_url(url: str) -> dict:
    from tools.browser_control import open_url
    return open_url(url)


def _wrap_click_element_by_vision(description: str, action_type: str = "click") -> dict:
    from tools.computer_control import click_element_by_vision
    return click_element_by_vision(description, action_type)


def _wrap_search_google(query: str) -> dict:
    from tools.browser_control import search_google
    return search_google(query)


def _wrap_search_twitter(query: str, limit: int | str = 5) -> dict:
    from tools.mxh_tools import search_twitter
    return search_twitter(query, int(limit))


def _wrap_read_reddit_post(subreddit: str, limit: int | str = 5) -> dict:
    from tools.mxh_tools import read_reddit_post
    return read_reddit_post(subreddit, int(limit))


def _wrap_get_youtube_transcript(video_url: str) -> dict:
    from tools.mxh_tools import get_youtube_transcript
    return get_youtube_transcript(video_url)


def _wrap_search_bilibili(query: str, limit: int | str = 5) -> dict:
    from tools.mxh_tools import search_bilibili
    return search_bilibili(query, int(limit))


def _wrap_read_webpage_jina(url: str) -> dict:
    from tools.mxh_tools import read_webpage_jina
    return read_webpage_jina(url)


async def _wrap_spawn_subagent(task: str, focus_files: list[str] | None = None) -> dict:
    from agents.subagent_service import run_subagent
    return await run_subagent(task, focus_files)


def _wrap_read_skill(name: str) -> dict:
    from skills.skills_manager import SkillsManager
    return SkillsManager().read_skill_content(name)


def _wrap_skill_manage(action: str, name: str, content: str = "") -> dict:
    from skills.skills_manager import SkillsManager
    return SkillsManager().manage_skill(action, name, content)


# ─────────────────────────────────────────────────────────────────────────────
# INITIALIZE & REGISTER ALL SYSTEM TOOLS
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_TOOLS = [
    {
        "name": "execute_command",
        "fn": _wrap_execute_command,
        "schema": {
            "name": "execute_command",
            "description": "Chạy lệnh shell (cmd/powershell trên Windows).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Lệnh cmd hoặc powershell cần thực thi."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "name": "write_to_file",
        "fn": _wrap_write_to_file,
        "schema": {
            "name": "write_to_file",
            "description": "Ghi nội dung vào một file trên máy tính.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Đường dẫn tới file cần tạo hoặc ghi đè."},
                    "content": {"type": "string", "description": "Nội dung cần viết vào file."},
                    "overwrite": {"type": "boolean", "description": "Có cho phép ghi đè nếu file đã tồn tại hay không."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "name": "read_file",
        "fn": _wrap_read_file,
        "schema": {
            "name": "read_file",
            "description": "Đọc nội dung một file văn bản hoặc tài liệu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Đường dẫn tới file."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "name": "mouse_click",
        "fn": _wrap_mouse_click,
        "schema": {
            "name": "mouse_click",
            "description": "Click chuột tại tọa độ x, y trên màn hình.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Tọa độ X."},
                    "y": {"type": "integer", "description": "Tọa độ Y."},
                    "button": {"type": "string", "description": "Nút chuột: 'left' hoặc 'right'."},
                    "double_click": {"type": "boolean", "description": "Có phải click đúp hay không."}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "name": "mouse_move",
        "fn": _wrap_mouse_move,
        "schema": {
            "name": "mouse_move",
            "description": "Di chuyển con trỏ chuột đến tọa độ x, y.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Tọa độ X."},
                    "y": {"type": "integer", "description": "Tọa độ Y."}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "name": "mouse_scroll",
        "fn": _wrap_mouse_scroll,
        "schema": {
            "name": "mouse_scroll",
            "description": "Cuộn màn hình lên hoặc xuống.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clicks": {"type": "integer", "description": "Số nấc cuộn chuột (ví dụ: 3, 5, 10). Mặc định là 1."},
                    "direction": {"type": "string", "enum": ["up", "down"], "description": "Hướng cuộn: 'up' (lên) hoặc 'down' (xuống). Mặc định là 'down'."},
                    "x": {"type": "integer", "description": "Tọa độ X cần di chuyển chuột tới trước khi cuộn (tùy chọn)."},
                    "y": {"type": "integer", "description": "Tọa độ Y cần di chuyển chuột tới trước khi cuộn (tùy chọn)."}
                },
                "required": ["clicks"]
            }
        }
    },
    {
        "name": "mouse_drag",
        "fn": _wrap_mouse_drag,
        "schema": {
            "name": "mouse_drag",
            "description": "Kéo và thả chuột từ vị trí hiện tại đến tọa độ x, y.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Tọa độ X đích kéo thả chuột tới."},
                    "y": {"type": "integer", "description": "Tọa độ Y đích kéo thả chuột tới."},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Phím nhấn giữ chuột: 'left' (trái), 'right' (phải), 'middle' (giữa). Mặc định là 'left'."},
                    "duration": {"type": "number", "description": "Thời gian thực hiện hành động kéo rê chuột (tính bằng giây). Mặc định là 0.5."}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "name": "keyboard_type",
        "fn": _wrap_keyboard_type,
        "schema": {
            "name": "keyboard_type",
            "description": "Gõ một chuỗi văn bản từ bàn phím.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Văn bản cần gõ."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "name": "keyboard_press",
        "fn": _wrap_keyboard_press,
        "schema": {
            "name": "keyboard_press",
            "description": "Ấn một phím hoặc tổ hợp phím ảo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {"type": "string", "description": "Phím hoặc tổ hợp phím (ví dụ: 'enter', 'ctrl+c')."}
                },
                "required": ["keys"]
            }
        }
    },
    {
        "name": "open_application",
        "fn": _wrap_open_application,
        "schema": {
            "name": "open_application",
            "description": "Mở một ứng dụng trên hệ điều hành.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Tên ứng dụng cần mở."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "name": "open_url",
        "fn": _wrap_open_url,
        "schema": {
            "name": "open_url",
            "description": "Mở một đường dẫn liên kết URL (trang web, bài hát youtube, v.v.) bằng trình duyệt mặc định của hệ thống.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Địa chỉ URL cần mở (ví dụ: 'https://youtube.com')."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "name": "click_element_by_vision",
        "fn": _wrap_click_element_by_vision,
        "schema": {
            "name": "click_element_by_vision",
            "description": "Sử dụng thị giác máy tính (VLM) để định vị và tương tác chuột (click, click đúp, di chuột) vào một phần tử trên màn hình dựa trên mô tả trực quan của phần tử đó.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Mô tả trực quan của phần tử cần tương tác (ví dụ: 'Nút đăng nhập màu xanh', 'Biểu tượng Google Chrome trên màn hình')."},
                    "action_type": {"type": "string", "enum": ["click", "double_click", "move"], "description": "Hành động mong muốn thực hiện (mặc định là 'click')."}
                },
                "required": ["description"]
            }
        }
    },
    {
        "name": "search_google",
        "fn": _wrap_search_google,
        "schema": {
            "name": "search_google",
            "description": "Tìm kiếm google qua trình duyệt mặc định.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa tìm kiếm."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "name": "search_twitter",
        "fn": _wrap_search_twitter,
        "schema": {
            "name": "search_twitter",
            "description": "Tìm kiếm các thảo luận, tin tức gần đây trên Twitter/X.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa tìm kiếm."},
                    "limit": {"type": "integer", "description": "Số lượng bài đăng muốn lấy (mặc định 5)."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "name": "read_reddit_post",
        "fn": _wrap_read_reddit_post,
        "schema": {
            "name": "read_reddit_post",
            "description": "Đọc các bài đăng hot nhất trên một Subreddit của Reddit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subreddit": {"type": "string", "description": "Tên Subreddit (ví dụ: 'python', 'funny')."},
                    "limit": {"type": "integer", "description": "Số lượng bài đăng muốn lấy (mặc định 5)."}
                },
                "required": ["subreddit"]
            }
        }
    },
    {
        "name": "get_youtube_transcript",
        "fn": _wrap_get_youtube_transcript,
        "schema": {
            "name": "get_youtube_transcript",
            "description": "Tải transcript/phụ đề của một video YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_url": {"type": "string", "description": "Địa chỉ URL đầy đủ của video."}
                },
                "required": ["video_url"]
            }
        }
    },
    {
        "name": "search_bilibili",
        "fn": _wrap_search_bilibili,
        "schema": {
            "name": "search_bilibili",
            "description": "Tìm kiếm video và tin tức trên Bilibili.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa tìm kiếm."},
                    "limit": {"type": "integer", "description": "Số lượng video muốn lấy (mặc định 5)."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "name": "read_webpage_jina",
        "fn": _wrap_read_webpage_jina,
        "schema": {
            "name": "read_webpage_jina",
            "description": "Đọc nội dung dưới dạng văn bản sạch (Markdown) của một trang web sử dụng dịch vụ Jina Reader API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Địa chỉ URL của trang web cần đọc."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "name": "spawn_subagent",
        "fn": _wrap_spawn_subagent,
        "schema": {
            "name": "spawn_subagent",
            "description": "Ủy quyền một tác vụ nghiên cứu mã nguồn hoặc phân tích tệp tin phức tạp sang một Agent phụ chạy ngầm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Tác vụ cụ thể cần nghiên cứu."},
                    "focus_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Danh sách các tệp tin quan trọng cần tập trung nghiên cứu."
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "name": "read_skill",
        "fn": _wrap_read_skill,
        "schema": {
            "name": "read_skill",
            "description": "Đọc nội dung và hướng dẫn thực hiện của một kỹ năng hệ thống (kỹ năng lưu dạng Markdown trong thư mục skills/).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Tên thư mục kỹ năng cần đọc (ví dụ: 'git-github-management')."}
                },
                "required": ["name"]
            }
        }
    },
    {
        "name": "skill_manage",
        "fn": _wrap_skill_manage,
        "schema": {
            "name": "skill_manage",
            "description": "Tạo mới, cập nhật nội dung hoặc xóa bỏ một kỹ năng hệ thống.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "update", "delete"], "description": "Hành động: 'create' (tạo mới), 'update' (cập nhật), 'delete' (xóa)."},
                    "name": {"type": "string", "description": "Tên kỹ năng (dạng slug, ví dụ: 'docker-management')."},
                    "content": {"type": "string", "description": "Nội dung Markdown hướng dẫn kỹ năng (bắt buộc khi action là create hoặc update)."}
                },
                "required": ["action", "name"]
            }
        }
    }
]

# Register all tools automatically on import
for tool_info in SYSTEM_TOOLS:
    register_tool(tool_info["name"], tool_info["fn"], tool_info["schema"])
