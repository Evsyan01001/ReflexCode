import time
import logging
from typing import Optional
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from app.config import settings
