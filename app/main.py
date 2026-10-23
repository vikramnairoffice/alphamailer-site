from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .admin_routes import router as admin_router
from .api_routes import router as api_router
from .fleet_routes import router as fleet_router, ui_router as fleet_ui_router
from .gradio_bridge import router as gradio_router, Bridge
from .google_oauth import router as google_oauth_router
from .config import get_settings
from .database import Base, engine


def create_app() -> FastAPI:
    app = FastAPI(title="URL Registry Admin")
    app.state.gradio_bridge = Bridge()

    @app.on_event("startup")
    async def on_startup():  # pragma: no cover
        Base.metadata.create_all(bind=engine)

    @app.get("/")
    async def root():  # pragma: no cover
        return RedirectResponse("/admin/")

    app.include_router(api_router)
    app.include_router(admin_router)
    app.include_router(fleet_router)
    app.include_router(fleet_ui_router)
    app.include_router(gradio_router)
    app.include_router(google_oauth_router)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    dashboard = Path(__file__).resolve().parents[2] / "Alphamailer-Android/build/web"
    if dashboard.is_dir():
        app.mount("/dashboard", StaticFiles(directory=dashboard, html=True), name="dashboard")

    return app


app = create_app()
