from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.achievements import apply_achievement_event
from ..core.errors import error_detail
from ..database import get_db
from .room import serialize_room
from .user import get_current_user, validate_student_id

router = APIRouter(prefix="/friends", tags=["friends"])


def serialize_friend(friend: models.Friend, unlocked_achievements: list[dict] | None = None) -> dict:
    return {
        "friend_id": friend.friend_id,
        "created_at": friend.created_at,
        "friend": friend.friend_user,
        "unlocked_achievements": unlocked_achievements or [],
    }


def are_already_friends(db: Session, user_id: int, friend_user_id: int) -> bool:
    return (
        db.query(models.Friend)
        .filter(
            models.Friend.user_id == user_id,
            models.Friend.friend_user_id == friend_user_id,
        )
        .first()
        is not None
    )


def create_friend_if_missing(db: Session, user_id: int, friend_user_id: int) -> None:
    if not are_already_friends(db, user_id, friend_user_id):
        db.add(models.Friend(user_id=user_id, friend_user_id=friend_user_id))


def serialize_friend_request(
    friend_request: models.FriendRequest,
    unlocked_achievements: list[dict] | None = None,
) -> dict:
    return {
        "request_id": friend_request.request_id,
        "status": friend_request.status,
        "created_at": friend_request.created_at,
        "responded_at": friend_request.responded_at,
        "requester": friend_request.requester,
        "receiver": friend_request.receiver,
        "unlocked_achievements": unlocked_achievements or [],
    }


@router.get("/", response_model=list[schemas.FriendOut])
def list_friends(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friends = (
        db.query(models.Friend)
        .filter(models.Friend.user_id == current_user.user_id)
        .order_by(models.Friend.created_at.desc())
        .all()
    )
    return [serialize_friend(friend) for friend in friends]


@router.get("/search/{student_id}", response_model=schemas.FriendUser)
def search_friend_by_student_id(
    student_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not validate_student_id(student_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID must be 9 digits")

    user = db.query(models.User).filter(models.User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@router.post("/", response_model=schemas.FriendOut, status_code=status.HTTP_201_CREATED)
def add_friend(
    friend_in: schemas.FriendCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not validate_student_id(friend_in.student_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID must be 9 digits")

    friend_user = db.query(models.User).filter(models.User.student_id == friend_in.student_id).first()
    if not friend_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if friend_user.user_id == current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add yourself as a friend")

    existing_friend = (
        db.query(models.Friend)
        .filter(
            models.Friend.user_id == current_user.user_id,
            models.Friend.friend_user_id == friend_user.user_id,
        )
        .first()
    )
    if existing_friend:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail("ALREADY_FRIEND", "이미 친구로 추가된 유저입니다."),
        )

    friend = models.Friend(
        user_id=current_user.user_id,
        friend_user_id=friend_user.user_id,
    )
    db.add(friend)
    unlocked_achievements = apply_achievement_event(db, current_user, "friend")
    db.commit()
    db.refresh(friend)
    return serialize_friend(friend, unlocked_achievements)


@router.get("/requests", response_model=list[schemas.FriendRequestOut])
def list_friend_requests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    requests = (
        db.query(models.FriendRequest)
        .filter(
            (
                (models.FriendRequest.receiver_id == current_user.user_id)
                | (models.FriendRequest.requester_id == current_user.user_id)
            ),
            models.FriendRequest.status == "pending",
        )
        .order_by(models.FriendRequest.created_at.desc())
        .all()
    )
    return [serialize_friend_request(friend_request) for friend_request in requests]


@router.post("/requests", response_model=schemas.FriendRequestOut, status_code=status.HTTP_201_CREATED)
def create_friend_request(
    request_in: schemas.FriendRequestCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not validate_student_id(request_in.student_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID must be 9 digits")

    receiver = db.query(models.User).filter(models.User.student_id == request_in.student_id).first()
    if not receiver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if receiver.user_id == current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot request yourself as a friend")
    if are_already_friends(db, current_user.user_id, receiver.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail("ALREADY_FRIEND", "이미 친구로 추가된 유저입니다."),
        )

    existing_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.requester_id == current_user.user_id,
            models.FriendRequest.receiver_id == receiver.user_id,
            models.FriendRequest.status == "pending",
        )
        .first()
    )
    if existing_request:
        return serialize_friend_request(existing_request)

    reverse_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.requester_id == receiver.user_id,
            models.FriendRequest.receiver_id == current_user.user_id,
            models.FriendRequest.status == "pending",
        )
        .first()
    )
    if reverse_request:
        reverse_request.status = "accepted"
        reverse_request.responded_at = datetime.utcnow()
        create_friend_if_missing(db, current_user.user_id, receiver.user_id)
        create_friend_if_missing(db, receiver.user_id, current_user.user_id)
        unlocked_achievements = apply_achievement_event(db, current_user, "friend")
        apply_achievement_event(db, receiver, "friend")
        db.commit()
        db.refresh(reverse_request)
        return serialize_friend_request(reverse_request, unlocked_achievements)

    friend_request = models.FriendRequest(
        requester_id=current_user.user_id,
        receiver_id=receiver.user_id,
    )
    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)
    return serialize_friend_request(friend_request)


@router.post("/requests/{request_id}/accept", response_model=schemas.FriendRequestOut)
def accept_friend_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.request_id == request_id,
            models.FriendRequest.receiver_id == current_user.user_id,
            models.FriendRequest.status == "pending",
        )
        .first()
    )
    if not friend_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")

    friend_request.status = "accepted"
    friend_request.responded_at = datetime.utcnow()
    create_friend_if_missing(db, friend_request.requester_id, friend_request.receiver_id)
    create_friend_if_missing(db, friend_request.receiver_id, friend_request.requester_id)
    unlocked_achievements = apply_achievement_event(db, current_user, "friend")
    apply_achievement_event(db, friend_request.requester, "friend")
    db.commit()
    db.refresh(friend_request)
    return serialize_friend_request(friend_request, unlocked_achievements)


@router.delete("/requests/{request_id}")
def delete_friend_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.request_id == request_id,
            (
                (models.FriendRequest.receiver_id == current_user.user_id)
                | (models.FriendRequest.requester_id == current_user.user_id)
            ),
            models.FriendRequest.status == "pending",
        )
        .first()
    )
    if not friend_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")

    friend_request.status = "rejected"
    friend_request.responded_at = datetime.utcnow()
    db.commit()
    return {"detail": "Friend request deleted"}


@router.get("/{friend_id}", response_model=schemas.FriendDetail)
def get_friend_detail(
    friend_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend = (
        db.query(models.Friend)
        .filter(
            models.Friend.friend_id == friend_id,
            models.Friend.user_id == current_user.user_id,
        )
        .first()
    )
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")

    friend_user = friend.friend_user
    equipped_items = (
        db.query(models.UserRoomEquipped)
        .filter(models.UserRoomEquipped.user_id == friend_user.user_id)
        .order_by(models.UserRoomEquipped.item_type)
        .all()
    )
    room = serialize_room(friend_user, equipped_items, db)
    return {
        "friend": friend_user,
        "character": room["character"],
        "room_owner_id": friend_user.user_id,
        "room": room,
    }


@router.delete("/{friend_id}")
def delete_friend(
    friend_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend = (
        db.query(models.Friend)
        .filter(
            models.Friend.friend_id == friend_id,
            models.Friend.user_id == current_user.user_id,
        )
        .first()
    )
    if not friend:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")

    db.delete(friend)
    db.commit()
    return {"detail": "Friend deleted"}
