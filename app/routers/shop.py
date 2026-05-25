from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/shop", tags=["shop"])


def serialize_shop_item(
    item: models.RoomItem,
    owned_item_ids: set[int],
    equipped_item_ids: set[int],
) -> dict:
    return {
        "item_id": item.item_id,
        "name": item.name,
        "item_type": item.item_type,
        "image": item.image,
        "price": item.price,
        "is_default": item.is_default,
        "created_at": item.created_at,
        "owned": item.is_default or item.item_id in owned_item_ids,
        "equipped": item.item_id in equipped_item_ids,
    }


@router.post("/items", response_model=schemas.RoomItemOut, status_code=status.HTTP_201_CREATED)
def create_room_item(item_in: schemas.RoomItemCreate, db: Session = Depends(get_db)):
    item = models.RoomItem(**item_in.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[schemas.ShopItemOut])
def list_shop_items(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(models.RoomItem)
        .order_by(models.RoomItem.item_type, models.RoomItem.price, models.RoomItem.item_id)
        .all()
    )
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
        "item": item,
        "coin": current_user.coin,
    }
