from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter(prefix="/settings", tags=["settings"])


class DemoAdmin(BaseModel):
    username: str
    display_name: str


class AppSettings(BaseModel):
    app_name: str
    env: str
    admin: DemoAdmin
    auth_mode: str  # "demo_no_auth" for this build
    note: str


@router.get("", response_model=AppSettings)
def get_settings() -> AppSettings:
    return AppSettings(
        app_name=settings.APP_NAME,
        env=settings.APP_ENV,
        admin=DemoAdmin(
            username=settings.ADMIN_USERNAME,
            display_name=settings.ADMIN_DISPLAY_NAME,
        ),
        auth_mode="demo_no_auth",
        note=(
            "This is a single-operator demo build. No login is required. "
            "All actions are attributed to the demo admin above. "
            "Production hardening would add authentication and per-user roles."
        ),
    )
