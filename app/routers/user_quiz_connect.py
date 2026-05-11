from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/user-quiz-connect", tags=["user-quiz-connect"])


@router.post("/", response_model=schemas.UserQuizConnect)
def create_user_quiz_connect(item_in: schemas.UserQuizConnectCreate, db: Session = Depends(get_db)):
    item = models.UserQuizConnect(**item_in.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/", response_model=list[schemas.UserQuizConnect])
def list_user_quiz_connect(db: Session = Depends(get_db)):
    return db.query(models.UserQuizConnect).all()


@router.get("/{user_quiz_id}", response_model=schemas.UserQuizConnect)
def get_user_quiz_connect(user_quiz_id: int, db: Session = Depends(get_db)):
    item = db.query(models.UserQuizConnect).filter(models.UserQuizConnect.user_quiz_id == user_quiz_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="User quiz connect record not found")
    return item


@router.delete("/{user_quiz_id}")
def delete_user_quiz_connect(user_quiz_id: int, db: Session = Depends(get_db)):
    item = db.query(models.UserQuizConnect).filter(models.UserQuizConnect.user_quiz_id == user_quiz_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="User quiz connect record not found")
    db.delete(item)
    db.commit()
    return {"detail": "User quiz record deleted"}
