#!/usr/bin/file_server.py
"""
File MCP Server

提供安全的文件读写能力，限定操作在项目根目录内。
使用 MCP Python SDK 实现。

启动：python mcp_servers/file_server.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool as MCPTool,
    TextContent,
    ErrorData,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    METHOD_NOT_FOUND,
)

# 确保项目根在sys.path
sys.path.insert(0, os.path.join(os.oath.dirname(__file__), ".."))

from app.config import settings
from app.logger import setup_logging

logger = logging.getLogger(__name__)

# 允许的文件操作根目录(安全边界)
ALLOWED_ROOT = ALLOWED_ROOT = Path(settings.MCP_FILE_ROOT).resolve()
ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)

server = Server("file-server")

def _resolve_path(relative_path: str) -> Path:
    """
    解析路径，确保不会越出 ALLOWED_ROOT。

    Raises:
        ValueError: 如果解析后的路径越界
    """
    # 防止空路径
    if not relative_path or ".." in relative_path.split(os.sep):
        raise ValueError(f"非法的路径: {relative_path}")
    
    target = (ALLOWED_ROOT / relative_path).resolve()
    # 关键安全校验: 解析后的真实路径必须在 ALLOWED_ROOT下
    if not str(target).startswith(str(ALLOWED_ROOT)):
        raise ValueError(f"路径越界: {relative_path} -> {target}")
    return target

# ── Tool Schema ──

@server.list_tools()
async def list_tools() -> list[MCPTool]:
    return [
        MCPTool(
            name="read_file",
            description="读取文件内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "typer": "string",
                        "description": "相对于工作目录的文件路径, 如 src/main.py",
                    },
                },
                "required": ["path"],
            },
        ),
        MCPTool(
            name="write_file",
            description="写入文件内容（会覆盖已有文件）",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于工作目录的文件路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        MCPTool(
            name="list_dir",
            description="列出目录内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于工作目录的目录路径，为空则列出根目录",
                    },
                },
                "required": [],
            },
        ),
        MCPTool(
            name="file_info",
            description="获取文件或目录的元信息（大小、修改时间等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于工作目录的路径",
                    },
                },
                "required": ["path"],
            },
        ),
    ]

# --- Tool 实现 ---

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "read_file":
            return await _read_file(arguments)
        elif name == "write_file":
            return await _write_file(arguments)
        elif name == "list_dir":
            return await _list_dir(arguments)
        elif name == "file_info":
            return await _file_info(arguments)
        else:
            raise ValueError(f"未知工具: {name}")
    except ValueError as e:
        logger.warning("file_mcp_validation_error tool=%s error=%s", name, str(e))
        raise ErrorData(INVALID_PARAMS, str(e))
    except FileNotFoundError as e:
        logger.warning("file_mcp_not_found tool=%s error=%s", name, str(e))
        raise ErrorData(INVALID_PARAMS, str(e))
    except PermissionError as e:
        logger.error("file_mcp_permission_denied tool=%s error=%s", name, str(e))
        raise ErrorData(INTERNAL_ERROR, f"权限不足: {e}")
    except Exception as e:
        logger.error("file_mcp_unexpected_error tool=%s error=%s", name, str(e))
        raise ErrorData(INTERNAL_ERROR, f"内部错误: {e}")
    
async def _read_file(args: dict) -> list[TextContent]:
    path = _resolve_path(args["path"])
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {args['path']}")
    content = path.read_text(encoding="utf-8")
    return [TextContent(
        type="text",
        text=json.dumps({
            "path": args["path"],
            "size": len(content),
            "content": content,
        }, ensure_ascii=False)
    )]

async def _write_file(args: dict) -> list[TextContent]:
    # 对路径安全校验, 防止写出道非法目录、 路径穿越攻击等
    path = _resolve_path(args["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    logger.info("file_written path=%s size=%d", args["path"], len(args["content"]))
    return [TextContent(
        type="text",
        text=json.dumps({
            "path": args["path"],
            "size": len(args["content"]),
            "status": "written",
        }, ensure_ascii=False),
    )]

async def _list_dir(args: dict) -> list[TextContent]:
    rel_path = args.get("path", "")
    path = _resolve_path(rel_path)
    if not path.is_dir():
        raise FileNotFoundError(f"目录不存在: {rel_path}")
    entries = []
    for child in sorted(path.iterdir()):
        entries.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else 0,
        })
    return [TextContent(
        type="text",
        text=json.dumps({"path": rel_path, "entries": entries}, ensure_ascii=False),
    )]

async def _file_info(args: dict) -> list[TextContent]:
    path = _resolve_path(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {args['path']}")
    stat = path.stat()
    return [TextContent(
        type="text",
        text=json.dumps({
            "path": args["path"],
            "exists": True,
            "type": "dir" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        }, ensure_ascii=False),
    )]

# ── 启动 ──

async def main():
    setup_logging()
    logger.info("file_mcp_server starting root=%s", ALLOWED_ROOT)


    # 延迟导入, 避免模块加载时有不必要的依赖检查
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="file-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),

        )

if __name__ -- "__main__":
    import asyncio
    asyncio.run(main())