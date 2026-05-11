from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("/", response_model=schemas.Character)
def create_character(character_in: schemas.CharacterCreate, db: Session = Depends(get_db)):
    character = models.Character(**character_in.dict())
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.get("/", response_model=list[schemas.Character])
def list_characters(db: Session = Depends(get_db)):
    return db.query(models.Character).all()


@router.get("/{character_id}", response_model=schemas.Character)
def get_character(character_id: int, db: Session = Depends(get_db)):
    character = db.query(models.Character).filter(models.Character.character_id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.put("/{character_id}", response_model=schemas.Character)
def update_character(character_id: int, character_in: schemas.CharacterUpdate, db: Session = Depends(get_db)):
    character = db.query(models.Character).filter(models.Character.character_id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    for field, value in character_in.dict(exclude_unset=True).items():
        setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return character


@router.delete("/{character_id}")
def delete_character(character_id: int, db: Session = Depends(get_db)):
    character = db.query(models.Character).filter(models.Character.character_id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(character)
    db.commit()
    return {"detail": "Character deleted"}
