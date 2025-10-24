from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .admin_routes import router as admin_router
from .api_routes import router as api_router
from .config import get_settings
from .database import Base, engine


def create_app() -> FastAPI:
    app = FastAPI(title="URL Registry Admin")

    @app.on_event("startup")
    async def on_startup():  # pragma: no cover
        Base.metadata.create_all(bind=engine)

    @app.get("/")
    async def root():  # pragma: no cover
        return RedirectResponse("/admin/")

    app.include_router(api_router)
    app.include_router(admin_router)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app


app = create_app()
