from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user, validate_student_id

router = APIRouter(prefix="/friends", tags=["friends"])


def serialize_friend(friend: models.Friend) -> dict:
    return {
        "friend_id": friend.friend_id,
        "created_at": friend.created_at,
        "friend": friend.friend_user,
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Friend already added")

    friend = models.Friend(
        user_id=current_user.user_id,
        friend_user_id=friend_user.user_id,
    )
    db.add(friend)
    db.commit()
    db.refresh(friend)
    return serialize_friend(friend)


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
