import argparse
import sys

from app import auth, models
from app.database import Base, engine, session_scope


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def create_admin(email: str, password: str) -> None:
    ensure_tables()
    with session_scope() as session:
        existing = session.query(models.User).filter(models.User.email == email).one_or_none()
        if existing:
            print("User already exists")
            return
        user = models.User(
            email=email,
            hashed_password=auth.hash_password(password),
            is_admin=True,
        )
        session.add(user)
    print("Admin user created")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Seed an admin user")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    args = parser.parse_args(argv)

    create_admin(args.email.lower(), args.password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
