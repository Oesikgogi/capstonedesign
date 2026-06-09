from . import models
from .database import SessionLocal


WALLPAPER_ITEMS = [
    ("wallpaper-basic", "기본", 0, True),
    ("wallpaper-blue", "파란 벽지", 200, False),
    ("wallpaper-gray", "회색 벽지", 200, False),
    ("wallpaper-green", "초록 벽지", 200, False),
    ("wallpaper-meolbow", "멀바우 벽지", 200, False),
    ("wallpaper-pink", "분홍 벽지", 200, False),
    ("wallpaper-purple", "보라 벽지", 200, False),
    ("wallpaper-red", "빨간 벽지", 200, False),
    ("wallpaper-teak", "티크 벽지", 200, False),
    ("wallpaper-whiteoak", "화이트오크 벽지", 200, False),
    ("wallpaper-yellow", "노란 벽지", 200, False),
]

WOOD_LABELS = [
    ("maple", "메이플"),
    ("merbau", "멀바우"),
    ("oak", "오크"),
    ("walnut", "월넛"),
    ("white-oak", "화이트오크"),
]

COLOR_LABELS = [
    ("blue", "파랑"),
    ("green", "초록"),
    ("pink", "핑크"),
    ("purple", "보라"),
    ("red", "빨강"),
    ("teal", "청록"),
    ("yellow", "노랑"),
]


def build_room_item_catalog() -> list[dict]:
    catalog = [
        {
            "item_key": item_key,
            "name": name,
            "item_type": "wallpaper",
            "image": f"/images/room/{item_key}.png",
            "price": price,
            "is_default": is_default,
        }
        for item_key, name, price, is_default in WALLPAPER_ITEMS
    ]

    catalog.append(
        {
            "item_key": "bed-basic",
            "name": "기본",
            "item_type": "bed",
            "image": "/images/room/bed-basic.png",
            "price": 0,
            "is_default": True,
        }
    )
    for wood_key, wood_label in WOOD_LABELS:
        for color_key, color_label in COLOR_LABELS:
            item_key = f"bed-{wood_key}-{color_key}"
            catalog.append(
                {
                    "item_key": item_key,
                    "name": f"{wood_label} {color_label}",
                    "item_type": "bed",
                    "image": f"/images/room/{item_key}.png",
                    "price": 200,
                    "is_default": False,
                }
            )

    catalog.append(
        {
            "item_key": "closet-basic",
            "name": "기본",
            "item_type": "closet",
            "image": "/images/room/closet-basic.png",
            "price": 0,
            "is_default": True,
        }
    )
    for wood_key, wood_label in WOOD_LABELS:
        item_key = f"closet-{wood_key}"
        catalog.append(
            {
                "item_key": item_key,
                "name": wood_label,
                "item_type": "closet",
                "image": f"/images/room/{item_key}.png",
                "price": 200,
                "is_default": False,
            }
        )

    catalog.append(
        {
            "item_key": "table-basic",
            "name": "기본",
            "item_type": "table",
            "image": "/images/room/table-basic.png",
            "price": 0,
            "is_default": True,
        }
    )
    for wood_key, wood_label in WOOD_LABELS:
        for color_key, color_label in COLOR_LABELS:
            item_key = f"table-{wood_key}-{color_key}"
            catalog.append(
                {
                    "item_key": item_key,
                    "name": f"{wood_label} {color_label}",
                    "item_type": "table",
                    "image": f"/images/room/{item_key}.png",
                    "price": 200,
                    "is_default": False,
                }
            )

    return catalog


def load_room_items() -> list[dict]:
    return build_room_item_catalog()


def seed_room_items() -> tuple[int, int]:
    room_items = load_room_items()
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
