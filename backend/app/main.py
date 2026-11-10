from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.services import scheduler as scheduler_service
from app.api import (
    health, deliveries, vehicles, incidents, risk, scan_runs,
    plans, simulations, actions, audit,
    copilot, context, customer_drafts,
    dashboard, analytics, settings as settings_api, auth as auth_api,
    _diag,
)

# Ensure all ORM models are registered on Base.metadata
from app.models import *  # noqa: F401,F403

logger = logging.getLogger("brainflow.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure schema + admin user exist (idempotent, safe for serverless)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:  # noqa: BLE001
        logger.exception("DB create_all failed")
    try:
        from app.services import auth_service
        db = SessionLocal()
        try:
            auth_service.ensure_admin_user(db)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.exception("Admin seed failed")
    scheduler_service.start_scheduler()
    try:
        yield
    finally:
        scheduler_service.stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="AI-powered logistics operations platform (demo build).",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    prefix = settings.API_PREFIX
    for r in (
        health.router, deliveries.router, vehicles.router,
        incidents.router, risk.router, scan_runs.router,
        plans.router, simulations.router,
        actions.router, audit.router,
        copilot.router, context.router, customer_drafts.router,
        dashboard.router, analytics.router,
        settings_api.router,
        auth_api.router,
        _diag.router,
    ):
        app.include_router(r, prefix=prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "docs": "/docs", "health": f"{prefix}/health"}

    return app


app = create_app()
