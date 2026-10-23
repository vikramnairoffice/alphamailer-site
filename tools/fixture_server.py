"""Ephemeral integration server. Never uses the operator's configured database."""
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--database", required=True)
parser.add_argument("--port", required=True, type=int)
args = parser.parse_args()
os.environ["DATABASE_URL"] = "sqlite:///" + args.database.replace("\\", "/")
os.environ["SESSION_SECRET"] = "isolated-browser-fixture-session"
os.environ["ENABLE_BROWSER_SEND"] = "false"
if not os.environ.get("API_TOKEN"):
    raise RuntimeError("Integration fixture requires a test-only API_TOKEN")

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User
from app.auth import hash_password
import uvicorn

Base.metadata.create_all(engine)
with SessionLocal() as db:
    if not db.query(User).first():
        db.add(User(email="fixture@example.com", hashed_password=hash_password("fixture-password"), is_admin=True))
        db.commit()
uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
engine.dispose()
