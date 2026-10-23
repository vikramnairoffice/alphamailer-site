from functools import lru_cache
import os


class Settings:
    def __init__(self) -> None:
        db_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
        # Render may provide 'postgres://' which SQLAlchemy expects as 'postgresql://' 
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        self.database_url = db_url
        self.api_token = os.getenv("API_TOKEN")
        self.session_secret = os.getenv("SESSION_SECRET")
        self.session_cookie_name = os.getenv("SESSION_COOKIE_NAME", "url_registry_session")
        # number of minutes to consider an instance active
        self.active_minutes = int(os.getenv("ACTIVE_MINUTES", "15"))
        self.enable_browser_send = os.getenv("ENABLE_WORKER_DELIVERY", os.getenv("ENABLE_BROWSER_SEND", "false")).lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
