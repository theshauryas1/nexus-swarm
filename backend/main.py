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

# ─── CORS ─────────────────────────────────────────────────────────
allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip() and origin.strip() != "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
