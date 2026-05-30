"""
NexusSwarm — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware

from config import get_settings
from limiter import limiter
from memory.db_client import close_db, get_engine, ping_db
from memory.redis_client import close_redis, get_redis
from routes import router

# ─── Structured logging ───────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger(__name__)

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def parse_csv_setting(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip() and item.strip() != "*"
    ]


# ─── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    settings = get_settings()

    logger.info("🚀 NexusSwarm starting up")
    logger.info("LLM provider: %s", settings.resolved_provider)

    # Connect Redis
    redis = await get_redis()
    logger.info("✅ Redis ready")

    # Verify DB
    db_ok = await ping_db()
    if db_ok:
        logger.info("✅ PostgreSQL ready")
    else:
        logger.warning("⚠️  PostgreSQL not reachable — check connection")

    # Initialize S3 client
    from memory.file_storage import get_storage_client
    s3_client = get_storage_client()
    if settings.s3_bucket and s3_client:
        logger.info("✅ Amazon S3 Storage ready, bucket: %s", settings.s3_bucket)
    elif settings.s3_bucket:
        logger.warning("⚠️ S3 bucket configured but client failed to initialize")

    yield

    # Shutdown
    logger.info("🛑 NexusSwarm shutting down")
    await close_redis()
    await close_db()


# ─── App ──────────────────────────────────────────────────────────
settings = get_settings()

app = FastAPI(
    title="NexusSwarm",
    description=(
        "Hierarchical Multi-Agent Governance System. "
        "Head Orchestrator → Pipeline Managers → Worker Agents."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    if "X-Powered-By" in response.headers:
        del response.headers["X-Powered-By"]
    return response

# ─── Rate Limiting ────────────────────────────────────────────────
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "retry_after", 60)
    response = JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded. Retry after {retry_after} seconds."}
    )
    response.headers["Retry-After"] = str(retry_after)
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Rejected invalid request", path=str(request.url.path), errors=exc.errors())
    return JSONResponse(
        status_code=400,
        content=jsonable_encoder({"detail": "Invalid request payload.", "errors": exc.errors()}),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error", path=str(request.url.path))
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong."},
    )

# ─── CORS ─────────────────────────────────────────────────────────
allowed_origins = parse_csv_setting(settings.cors_allowed_origins)
allowed_methods = parse_csv_setting(settings.cors_allowed_methods) or ["GET", "POST"]
allowed_headers = parse_csv_setting(settings.cors_allowed_headers) or ["Content-Type", "Authorization"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)

trusted_hosts = parse_csv_setting(settings.trusted_hosts) or ["localhost", "127.0.0.1", "testserver"]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts,
)

# ─── Routes ───────────────────────────────────────────────────────
app.include_router(router)


# ─── Root ─────────────────────────────────────────────────────────
@app.get("/", tags=["system"])
@limiter.limit("60/minute")
async def root(request: Request):
    return {
        "name":        "NexusSwarm",
        "version":     "1.0.0",
        "description": "Hierarchical Multi-Agent Governance System",
        "docs":        "/docs",
        "health":      "/health",
        "websocket":   "ws://localhost:8000/ws/agents",
    }
