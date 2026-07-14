from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ── Environment ──
    ENVIRONMENT: str = "development"     # development | production
    
    # ── DeepSeek ──
    DEEPSEEK_API_KEY: str = "sk-1e149a80014644d8a5349335f9db86dc"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"
    
    # ── MCP Server ──
    MCP_FILE_ROOT: str = "./workspace"          # File MCP 允许操作的根目录
    GIT_REPO_PATH: str = "."                    # Git MCP 操作的仓库路径

    # ── LangGraph ──
    MAX_RETRY: int = 3
    STATE_PERSIST_PATH: str = "./data/states"

    # ── Logging ──
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()