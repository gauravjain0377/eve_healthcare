from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import setup_logging, RequestIDMiddleware
from app.core.exceptions import AppException
from app.core.cache import cache
from app.api.v1.api import api_router
from app.api.v1.endpoints.payments import router as payments_router

# Setup structured logging
setup_logging()
logger = logging.getLogger("eve_healthcare.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("EVE Healthcare Backend Service initialized successfully.")
    yield
    logger.info("Shutting down EVE Healthcare Backend Service.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "**EVE Healthcare Backend Service**\n\n"
        "A robust RESTful API for diagnostic test bookings and simulated payments.\n\n"
        "### Features\n"
        "- **Authentication**: JWT-based auth with RBAC (Patients and Administrators).\n"
        "- **Diagnostic Centres & Tests**: Centre catalogs, tests management, and dynamic pricing.\n"
        "- **Booking Engine**: State machine (`PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`), future-date validation, ownership protection.\n"
        "- **Simulated Payments**: Payment processing with client-side idempotency.\n"
        "- **Idempotent Webhook**: Gateway webhook processing with duplicate protection and state safety.\n"
        "- **Observability & Bonus**: Structured logging, request ID tracing, sliding-window rate limiting, and Redis caching."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "error_code": exc.error_code,
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        },
        headers=exc.headers
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err["loc"])
        errors.append({"field": field, "message": err["msg"], "type": err["type"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "error_code": "VALIDATION_ERROR",
            "detail": "Invalid request parameters.",
            "errors": errors,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Health Check
@app.get("/health", tags=["System"])
@app.get("/", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "redis_connected": cache._is_redis_available
    }


# Include V1 Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Top-level route aliases matching direct assignment spec (/payments/ and /payments/webhook/)
app.include_router(payments_router, prefix="/payments", tags=["Payments (Assignment Spec Root)"])
