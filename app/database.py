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
    table_names = inspector.get_table_names()
    if "users" not in table_names:
        return

    existing_user_columns = {column["name"] for column in inspector.get_columns("users")}
    required_user_columns = {
        "coin": "INTEGER DEFAULT 0",
        "heart": "INTEGER DEFAULT 5",
        "heart_updated_at": "TIMESTAMP",
        "is_admin": "BOOLEAN DEFAULT FALSE",
        "graduated_at": "TIMESTAMP",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_user_columns.items():
            if column_name not in existing_user_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))

        connection.execute(text("UPDATE users SET coin = 0 WHERE coin IS NULL"))
        connection.execute(text("UPDATE users SET heart = 5 WHERE heart IS NULL"))
        connection.execute(text("UPDATE users SET heart_updated_at = CURRENT_TIMESTAMP WHERE heart_updated_at IS NULL"))
        connection.execute(text("UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL"))

    if "minigame_results" in table_names:
        existing_minigame_columns = {column["name"] for column in inspector.get_columns("minigame_results")}
        required_minigame_columns = {
            "play_session_id": "VARCHAR",
            "mode": "VARCHAR",
            "ended_reason": "VARCHAR",
        }
        with engine.begin() as connection:
            for column_name, column_type in required_minigame_columns.items():
                if column_name not in existing_minigame_columns:
                    connection.execute(text(f"ALTER TABLE minigame_results ADD COLUMN {column_name} {column_type}"))

    if "characters" in table_names:
        existing_character_columns = {column["name"] for column in inspector.get_columns("characters")}
        required_character_columns = {
            "state": "VARCHAR DEFAULT 'basic1'",
            "equipped_skin_key": "VARCHAR DEFAULT 'default'",
            "pending_evolution": "BOOLEAN DEFAULT FALSE",
            "skipped_meal_count": "INTEGER DEFAULT 0",
            "hungry_state": "BOOLEAN DEFAULT FALSE",
            "meal_health_date": "DATE",
            "last_checked_meal_slot": "VARCHAR",
            "applied_penalty_count": "INTEGER DEFAULT 0",
        }
        with engine.begin() as connection:
            for column_name, column_type in required_character_columns.items():
                if column_name not in existing_character_columns:
                    connection.execute(text(f"ALTER TABLE characters ADD COLUMN {column_name} {column_type}"))

            connection.execute(text("UPDATE characters SET state = 'basic1' WHERE state IS NULL"))
            connection.execute(text("UPDATE characters SET equipped_skin_key = 'default' WHERE equipped_skin_key IS NULL"))
            connection.execute(text("UPDATE characters SET pending_evolution = FALSE WHERE pending_evolution IS NULL"))
            connection.execute(text("UPDATE characters SET skipped_meal_count = 0 WHERE skipped_meal_count IS NULL"))
            connection.execute(text("UPDATE characters SET hungry_state = FALSE WHERE hungry_state IS NULL"))
            connection.execute(text("UPDATE characters SET applied_penalty_count = 0 WHERE applied_penalty_count IS NULL"))

    if "room_items" in table_names:
        existing_room_item_columns = {column["name"] for column in inspector.get_columns("room_items")}
        with engine.begin() as connection:
            if "item_key" not in existing_room_item_columns:
                connection.execute(text("ALTER TABLE room_items ADD COLUMN item_key VARCHAR"))
            connection.execute(text("UPDATE room_items SET item_type = 'wallpaper' WHERE item_type = 'room'"))
            connection.execute(text("UPDATE room_items SET item_type = 'table' WHERE item_type = 'desk'"))

    if "user_room_equipped" in table_names:
        with engine.begin() as connection:
            connection.execute(text("UPDATE user_room_equipped SET item_type = 'wallpaper' WHERE item_type = 'room'"))
            connection.execute(text("UPDATE user_room_equipped SET item_type = 'table' WHERE item_type = 'desk'"))
