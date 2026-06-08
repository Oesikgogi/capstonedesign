from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .room import ensure_default_room_state
from .user import get_current_admin_user, get_current_user

router = APIRouter(prefix="/shop", tags=["shop"])

SHOP_ITEM_TYPES = [
    {"item_type": "wallpaper", "label": "벽지"},
    {"item_type": "bed", "label": "침대"},
    {"item_type": "closet", "label": "장롱"},
    {"item_type": "table", "label": "책상"},
]

SHOP_ITEM_TYPE_ALIASES = {
    item["item_type"]: item["item_type"]
    for item in SHOP_ITEM_TYPES
}
SHOP_ITEM_TYPE_ALIASES.update({item["label"]: item["item_type"] for item in SHOP_ITEM_TYPES})
SHOP_ITEM_TYPE_ALIASES.update({
    "room": "wallpaper",
    "마이룸방": "wallpaper",
    "desk": "table",
    "책상": "table",
})


def normalize_item_type(item_type: str) -> str:
    normalized = SHOP_ITEM_TYPE_ALIASES.get(item_type.strip())
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item type")
    return normalized


def serialize_shop_item(
    item: models.RoomItem,
    owned_item_ids: set[int],
    equipped_item_ids: set[int],
) -> dict:
    item_type = normalize_item_type(item.item_type)
    item_key = item.item_key or f"{item_type}-{item.item_id}"
    return {
        "item_id": item.item_id,
        "item_key": item_key,
        "name": item.name,
        "item_type": item_type,
        "image": item.image,
        "price": item.price,
        "is_default": item.is_default,
        "created_at": item.created_at,
        "owned": item.is_default or item.item_id in owned_item_ids,
        "equipped": item.item_id in equipped_item_ids,
    }


@router.get("/item-types", response_model=list[schemas.ShopItemTypeOut])
def list_shop_item_types():
    return SHOP_ITEM_TYPES


@router.post("/items", response_model=schemas.RoomItemOut, status_code=status.HTTP_201_CREATED)
def create_room_item(
    item_in: schemas.RoomItemCreate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    item_data = item_in.dict()
    item_data["item_type"] = normalize_item_type(item_data["item_type"])
    item = models.RoomItem(**item_data)
    db.add(item)
    db.commit()
    if not item.item_key:
        item.item_key = f"{item.item_type}-{item.item_id}"
        db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[schemas.ShopItemOut])
def list_shop_items(
    item_type: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_default_room_state(db, current_user)
    db.commit()
    query = db.query(models.RoomItem)
    if item_type:
        normalized_type = normalize_item_type(item_type)
        type_values = [normalized_type]
        if normalized_type == "wallpaper":
            type_values.append("room")
        if normalized_type == "table":
            type_values.append("desk")
        query = query.filter(models.RoomItem.item_type.in_(type_values))

    items = query.order_by(models.RoomItem.item_type, models.RoomItem.price, models.RoomItem.item_id).all()
    owned_item_ids = {
        row.item_id
        for row in db.query(models.UserRoomItem.item_id)
        .filter(models.UserRoomItem.user_id == current_user.user_id)
        .all()
    }
    equipped_item_ids = {
        row.item_id
        for row in db.query(models.UserRoomEquipped.item_id)
        .filter(models.UserRoomEquipped.user_id == current_user.user_id)
        .all()
    }
    return [serialize_shop_item(item, owned_item_ids, equipped_item_ids) for item in items]


@router.post("/items/{item_id}/purchase", response_model=schemas.RoomItemPurchaseResult)
def purchase_room_item(
    item_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(models.RoomItem).filter(models.RoomItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room item not found")

    existing_item = (
        db.query(models.UserRoomItem)
        .filter(
            models.UserRoomItem.user_id == current_user.user_id,
            models.UserRoomItem.item_id == item.item_id,
        )
        .first()
    )
    if existing_item or item.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item already owned")

    if current_user.coin < item.price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough coins")

    if not item.item_key:
        item.item_type = normalize_item_type(item.item_type)
        item.item_key = f"{item.item_type}-{item.item_id}"
    current_user.coin -= item.price
    owned_item = models.UserRoomItem(
        user_id=current_user.user_id,
        item_id=item.item_id,
    )
    db.add(owned_item)
    db.commit()
    db.refresh(current_user)
    db.refresh(item)

    return {
        "detail": "Room item purchased",
        "item": serialize_shop_item(item, {item.item_id}, set()),
        "coin": current_user.coin,
    }
