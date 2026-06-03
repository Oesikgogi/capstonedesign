from datetime import datetime
from typing import Optional

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


def get_user_grade(xp_point: int) -> int:
    return max((xp_point or 0) // 1000 + 1, 1)


def serialize_room_item(item: models.RoomItem) -> dict:
    return {
        "item_id": item.item_id,
        "item_key": item.item_key or f"{item.item_type}_{item.item_id}",
        "name": item.name,
        "item_type": item.item_type,
        "image": item.image,
        "price": item.price,
        "is_default": item.is_default,
        "created_at": item.created_at,
    }


def serialize_equipped_item(equipped_item: models.UserRoomEquipped) -> dict:
    return {
        "equipped_id": equipped_item.equipped_id,
        "item_type": equipped_item.item_type,
        "equipped_at": equipped_item.equipped_at,
        "item": serialize_room_item(equipped_item.item),
    }


def serialize_owner(owner: models.User) -> dict:
    return {
        "user_id": owner.user_id,
        "student_id": owner.student_id,
        "nickname": owner.nickname,
        "image": owner.image,
        "xp_point": owner.xp_point,
        "grade": get_user_grade(owner.xp_point),
    }


def get_primary_character(db: Session, user_id: int) -> Optional[models.Character]:
    return (
        db.query(models.Character)
        .filter(models.Character.user_id == user_id)
        .order_by(models.Character.character_id.asc())
        .first()
    )


def serialize_character(owner: models.User, character: Optional[models.Character]) -> dict:
    return {
        "character_id": character.character_id if character else None,
        "character_name": character.character_name if character else None,
        "xp_point": owner.xp_point,
        "stage": character.stage if character else 1,
        "state": character.state if character else None,
    }


def serialize_room(owner: models.User, equipped_items: list[models.UserRoomEquipped], db: Session) -> dict:
    wallpaper_equipped = next((item for item in equipped_items if item.item_type == "room"), None)
    return {
        "owner": serialize_owner(owner),
        "character": serialize_character(owner, get_primary_character(db, owner.user_id)),
        "wallpaper": serialize_room_item(wallpaper_equipped.item) if wallpaper_equipped else None,
        "equipped_items": [serialize_equipped_item(item) for item in equipped_items],
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
    return serialize_room(current_user, equipped_items, db)


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
    return serialize_room(current_user, equipped_items, db)


@router.delete("/me/equip/{slot}", response_model=schemas.RoomView)
def unequip_room_item(
    slot: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    equipped_item = (
        db.query(models.UserRoomEquipped)
        .filter(
            models.UserRoomEquipped.user_id == current_user.user_id,
            models.UserRoomEquipped.item_type == slot,
        )
        .first()
    )
    if equipped_item:
        db.delete(equipped_item)
        db.commit()

    equipped_items = (
        db.query(models.UserRoomEquipped)
        .filter(models.UserRoomEquipped.user_id == current_user.user_id)
        .order_by(models.UserRoomEquipped.item_type)
        .all()
    )
    return serialize_room(current_user, equipped_items, db)


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
    return serialize_room(owner, equipped_items, db)


def serialize_guestbook_entry(entry: models.GuestbookEntry) -> dict:
    return {
        "entry_id": entry.entry_id,
        "room_owner_id": entry.room_owner_id,
        "writer_id": entry.writer_id,
        "writer_nickname": entry.writer.nickname,
        "content": entry.content,
        "created_at": entry.created_at,
    }


@router.get("/{user_id}/guestbook", response_model=schemas.GuestbookPage)
def list_guestbook_entries(
    user_id: int,
    cursor: Optional[str] = None,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_room_owner_or_404(user_id, db)
    require_room_access(owner, current_user, db)
    safe_limit = max(1, min(limit, 50))
    query = db.query(models.GuestbookEntry).filter(models.GuestbookEntry.room_owner_id == owner.user_id)
    if cursor:
        try:
            cursor_id = int(cursor)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor")
        query = query.filter(models.GuestbookEntry.entry_id < cursor_id)
    entries = query.order_by(models.GuestbookEntry.entry_id.desc()).limit(safe_limit + 1).all()
    page_entries = entries[:safe_limit]
    next_cursor = str(page_entries[-1].entry_id) if len(entries) > safe_limit and page_entries else None

    return {
        "items": [serialize_guestbook_entry(entry) for entry in page_entries],
        "next_cursor": next_cursor,
    }


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
    return serialize_guestbook_entry(entry)


@router.put("/guestbook/{entry_id}", response_model=schemas.GuestbookOut)
def update_guestbook_entry(
    entry_id: int,
    entry_in: schemas.GuestbookUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(models.GuestbookEntry).filter(models.GuestbookEntry.entry_id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guestbook entry not found")
    if entry.writer_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only writer can update this entry")

    entry.content = entry_in.content
    db.commit()
    db.refresh(entry)
    return serialize_guestbook_entry(entry)


@router.delete("/guestbook/{entry_id}")
def delete_guestbook_entry(
    entry_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(models.GuestbookEntry).filter(models.GuestbookEntry.entry_id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guestbook entry not found")
    if entry.writer_id != current_user.user_id and entry.room_owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only writer or room owner can delete this entry")

    db.delete(entry)
    db.commit()
    return {"detail": "Guestbook entry deleted"}
    if equip_in.slot and equip_in.slot != item.item_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot does not match item type")
