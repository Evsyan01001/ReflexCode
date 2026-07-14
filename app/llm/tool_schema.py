"""
统一的 Tool Schema 转换工具。

DeepSeek 使用与 OpenAI 相同的 Function Calling 格式，
所以我们直接用 OpenAI 的 tool schema 定义方式。
"""

from typing import Any

def function_tool(
        name: str,
        description: str,
        parameters: dict[str, Any],
) -> dict[str, Any]:
    """创建一个 OpenAI 兼容的 function tool 定义。"""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }

def parse_tool_call(message) -> list[dict]:
    """
    从模型返回的 message 中提取 tool call 信息。
    返回格式: [{"name": "...", "arguments": {...}}, ...]
    """
    if not message.tool_calls:
        return []

    calls = []
    for tc in message.tool_calls:
        import json
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            args = {"_raw": tc.function.arguments}

        calls.append({
            "id": tc.id,
            "name": tc.function.name,
            "arguments": args,
        })
    return calls

def format_tool_result(tool_call_id: str, result: Any) -> dict:
    """将工具执行结果转为 OpenAI 要求的 tool message 格式。"""
    import json
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": json.dumps(result, ensure_ascii=False),
    }