import json
from pathlib import Path

from . import models
from .database import SessionLocal


ROOM_ITEMS_PATH = Path(__file__).resolve().parent / "data" / "room_items.json"


def seed_room_items() -> tuple[int, int]:
    room_items = json.loads(ROOM_ITEMS_PATH.read_text(encoding="utf-8"))
    created = 0
    updated = 0

    db = SessionLocal()
    try:
        for item_data in room_items:
            item = (
                db.query(models.RoomItem)
                .filter(models.RoomItem.item_key == item_data["item_key"])
                .first()
            )
            if item:
                item.name = item_data["name"]
                item.item_type = item_data["item_type"]
                item.image = item_data["image"]
                item.price = item_data["price"]
                item.is_default = item_data["is_default"]
                updated += 1
                continue

            db.add(models.RoomItem(**item_data))
            created += 1

        db.commit()
    finally:
        db.close()

    return created, updated


if __name__ == "__main__":
    created_count, updated_count = seed_room_items()
    print(f"Created {created_count} room items, updated {updated_count} room items.")
