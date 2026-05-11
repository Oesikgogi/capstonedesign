import json
from pathlib import Path

from . import models
from .database import SessionLocal


SCHOOL_FOODS_PATH = Path(__file__).resolve().parent / "data" / "school_foods.json"


def seed_school_foods() -> tuple[int, int]:
    school_foods = json.loads(SCHOOL_FOODS_PATH.read_text(encoding="utf-8"))
    food_names = {item["name"] for item in school_foods}
    created = 0
    updated = 0

    db = SessionLocal()
    try:
        db.query(models.SchoolFood).filter(
            models.SchoolFood.name.notin_(food_names)
        ).delete(synchronize_session=False)

        for item_data in school_foods:
            item = (
                db.query(models.SchoolFood)
                .filter(models.SchoolFood.name == item_data["name"])
                .first()
            )
            if item:
                item.school_food_img = item_data["school_food_img"]
                item.type = item_data["type"]
                updated += 1
                continue

            db.add(
                models.SchoolFood(
                    name=item_data["name"],
                    school_food_img=item_data["school_food_img"],
                    type=item_data["type"],
                )
            )
            created += 1

        db.commit()
    finally:
        db.close()

    return created, updated


if __name__ == "__main__":
    created_count, updated_count = seed_school_foods()
    print(f"Created {created_count} school foods, updated {updated_count} school foods.")
