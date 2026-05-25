import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def _load_dotenv():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./boo_app.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)


connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_user_columns = {column["name"] for column in inspector.get_columns("users")}
    required_user_columns = {
        "coin": "INTEGER DEFAULT 0",
        "heart": "INTEGER DEFAULT 5",
        "heart_updated_at": "TIMESTAMP",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_user_columns.items():
            if column_name not in existing_user_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))

        connection.execute(text("UPDATE users SET coin = 0 WHERE coin IS NULL"))
        connection.execute(text("UPDATE users SET heart = 5 WHERE heart IS NULL"))
        connection.execute(text("UPDATE users SET heart_updated_at = CURRENT_TIMESTAMP WHERE heart_updated_at IS NULL"))
