"""FastAPI application entry point."""

import structlog
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware
from app.routers.chat import router as chat_router
from app.routers.vapi import router as vapi_router
from app.core.prompts import PROMPT_VERSION, PROMPT_CHANGELOG
from app.services.cache import cache_stats

# --- Structlog: JSON output for production ---
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

RESUME_PATH = Path(__file__).parent / "data" / "resume.pdf"

# --- Rate limiter ---
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI Persona API",
    description="Yashraj Kupekar's AI representative",
    version="1.0.0",
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Please try again later."},
    )


# --- Middleware ---
allowed_origins = [o.strip() for o in settings.frontend_url.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# --- Routers ---
app.include_router(chat_router)
app.include_router(vapi_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/cache/stats")
async def get_cache_stats():
    return cache_stats()


@app.get("/prompt/version")
async def prompt_version():
    return {
        "version": PROMPT_VERSION,
        "changelog": PROMPT_CHANGELOG,
    }


@app.get("/resume")
async def resume():
    return FileResponse(
        RESUME_PATH,
        media_type="application/pdf",
        filename="Yashraj_Kupekar_Resume.pdf",
    )
