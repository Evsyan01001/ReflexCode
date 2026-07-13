import sys
import logging
import json
from datetime import datetime, timezone

from app.config import settings

class StructuredFormatter(logging.Formatter):
    """结构化日志格式，后续可接入 ELK / Loki 等可观测性系统"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 如果有额外信息更新到log_entry
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        # 先检查exc_info是不是none，再检查异常类型是否存在
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)
            
def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO()))
    # 清除默认 handler，避免重复
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # 第三方库调低日志级别避免噪声
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)