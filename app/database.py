from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

SQLALCHEMY_DATABASE_URL = "sqlite:///./boo_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_sqlite_schema():
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        return

    required_user_columns = {
        "name": "VARCHAR DEFAULT ''",
        "email_verified": "BOOLEAN DEFAULT 0",
        "email_verified_at": "DATETIME",
    }
    required_school_food_columns = {
        "school_food_img": "VARCHAR",
    }

    with engine.begin() as connection:
        existing_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(users)")).fetchall()
        }
        for column_name, column_type in required_user_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                )

        existing_school_food_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(school_foods)")).fetchall()
        }
        for column_name, column_type in required_school_food_columns.items():
            if column_name not in existing_school_food_columns:
                connection.execute(
                    text(f"ALTER TABLE school_foods ADD COLUMN {column_name} {column_type}")
                )
