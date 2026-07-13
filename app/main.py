import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import setup_logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    setup_logging()
    logger.info("App starting up, environments=%s", settings.ENVIRONMENT)

    yield   # where app running on

    # 关闭时
    logger.info("App shutting down")

app = FastAPI(
    title="Code Review Loop Agent",
    version="0.1.0",
    description="An autonomous code dev-review-fix loop agent powered by LangGraph & MCP",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": time.time(),
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response= await call_next(request)
    duration = time.time() - start
    logger.info(
        "request method=%s path=%s status=%d duration=%.3fs",
        request.method, request.url.path, response.status_code, duration,
    )
    return response