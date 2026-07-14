import time
import logging
from typing import Optional
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from app.config import settings

logger = logging.getLogger(__name__)

class Client:
    """
    通过 OpenAI SDK 兼容方式接入 DeepSeek。
    DeepSeek 提供与 OpenAI 兼容的 API，只需修改 base_url。
    """

    def _init__(self):
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self.model = settings.DEEPSEEK_MODEL

    def chat(
            self,
            messages: list[dict],
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            stream: bool = False,
            tools: Optional[list[dict]] = None,
            tool_choice: Optional[str] = None,
    ) -> ChatCompletion | Stream[ChatCompletionChunk]:  # ← 返回类型：完整响应 或 流式块
        """
        统一的 chat completion 封装。

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 采样温度
            max_tokens: 最大生成 token
            stream: 是否 streaming
            tools: OpenAI 格式的 tool 定义列表
            tool_choice: "auto" / "none" / {"type": "function", "function": {"name": "..."}}
        """

        # 打包成kwargs传参更简洁、易维护
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=stream,
        )
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        start = time.time()
        try:
            response = self.client.chat.completions.create(**kwargs)
            elapsed = time.time() - start
            logger.info(
                "llm_request model=%s stream=%s tools=%s duration=%.2fs",
                self.model, stream, bool(tools), elapsed,
            )
            return response
        except Exception as e:
            logger.error("llm_request_failed error=%s", str(e))
            raise   # 不用return 在记录异常日志后,将异常重新抛出,使上层感知失败

    def chat_simple(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.chat(messages, stream=False)
        return response.choices[0].message.content or ""
