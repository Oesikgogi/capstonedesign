from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/rooms", tags=["rooms"])


def are_friends(db: Session, user_id: int, target_user_id: int) -> bool:
    return (
        db.query(models.Friend)
        .filter(
            (
                (models.Friend.user_id == user_id)
                & (models.Friend.friend_user_id == target_user_id)
            )
            | (
                (models.Friend.user_id == target_user_id)
                & (models.Friend.friend_user_id == user_id)
            )
        )
        .first()
        is not None
    )


def get_room_owner_or_404(user_id: int, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room owner not found")
    return user


def require_room_access(
    owner: models.User,
    current_user: models.User,
    db: Session,
) -> None:
    if owner.user_id == current_user.user_id:
        return
    if are_friends(db, current_user.user_id, owner.user_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only friends can access this room")


def serialize_room(owner: models.User, equipped_items: list[models.UserRoomEquipped]) -> dict:
    return {
        "owner": owner,
        "equipped_items": equipped_items,
    }


@router.get("/me", response_model=schemas.RoomView)
def get_my_room(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    equipped_items = (
        db.query(models.UserRoomEquipped)
        .filter(models.UserRoomEquipped.user_id == current_user.user_id)
        .order_by(models.UserRoomEquipped.item_type)
        .all()
    )
    return serialize_room(current_user, equipped_items)


@router.put("/me/equip", response_model=schemas.RoomView)
def equip_room_item(
    equip_in: schemas.RoomEquipRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(models.RoomItem).filter(models.RoomItem.item_id == equip_in.item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room item not found")

    owned_item = (
        db.query(models.UserRoomItem)
        .filter(
            models.UserRoomItem.user_id == current_user.user_id,
            models.UserRoomItem.item_id == item.item_id,
        )
        .first()
    )
    if not item.is_default and not owned_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is not owned")

    equipped_item = (
        db.query(models.UserRoomEquipped)
        .filter(
            models.UserRoomEquipped.user_id == current_user.user_id,
            models.UserRoomEquipped.item_type == item.item_type,
        )
        .first()
    )
    if equipped_item:
        equipped_item.item_id = item.item_id
        equipped_item.equipped_at = datetime.utcnow()
    else:
        equipped_item = models.UserRoomEquipped(
            user_id=current_user.user_id,
            item_type=item.item_type,
            item_id=item.item_id,
        )
        db.add(equipped_item)

    db.commit()
    db.refresh(current_user)
    equipped_items = (
        db.query(models.UserRoomEquipped)
        .filter(models.UserRoomEquipped.user_id == current_user.user_id)
        .order_by(models.UserRoomEquipped.item_type)
        .all()
    )
    return serialize_room(current_user, equipped_items)


@router.get("/{user_id}", response_model=schemas.RoomView)
def get_room(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_room_owner_or_404(user_id, db)
    require_room_access(owner, current_user, db)
    equipped_items = (
        db.query(models.UserRoomEquipped)
        .filter(models.UserRoomEquipped.user_id == owner.user_id)
        .order_by(models.UserRoomEquipped.item_type)
        .all()
    )
    return serialize_room(owner, equipped_items)


@router.get("/{user_id}/guestbook", response_model=list[schemas.GuestbookOut])
def list_guestbook_entries(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_room_owner_or_404(user_id, db)
    require_room_access(owner, current_user, db)
    entries = (
        db.query(models.GuestbookEntry)
        .filter(models.GuestbookEntry.room_owner_id == owner.user_id)
        .order_by(models.GuestbookEntry.created_at.desc())
        .all()
    )
    return [
        {
            "entry_id": entry.entry_id,
            "room_owner_id": entry.room_owner_id,
            "writer_id": entry.writer_id,
            "writer_nickname": entry.writer.nickname,
            "content": entry.content,
            "created_at": entry.created_at,
        }
        for entry in entries
    ]


@router.post("/{user_id}/guestbook", response_model=schemas.GuestbookOut, status_code=status.HTTP_201_CREATED)
def create_guestbook_entry(
    user_id: int,
    entry_in: schemas.GuestbookCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_room_owner_or_404(user_id, db)
    require_room_access(owner, current_user, db)
    entry = models.GuestbookEntry(
        room_owner_id=owner.user_id,
        writer_id=current_user.user_id,
        content=entry_in.content,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "entry_id": entry.entry_id,
        "room_owner_id": entry.room_owner_id,
        "writer_id": entry.writer_id,
        "writer_nickname": current_user.nickname,
        "content": entry.content,
        "created_at": entry.created_at,
    }
