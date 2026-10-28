from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import (
    health, deliveries, vehicles, incidents, risk, scan_runs,
    plans, simulations, actions, audit,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="AI-powered logistics operations platform (demo build).",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
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
    ):
        app.include_router(r, prefix=prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "docs": "/docs", "health": f"{prefix}/health"}

    return app


app = create_app()
