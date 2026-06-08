from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .character import get_or_create_my_character, serialize_my_character
from .user import get_current_admin_user

router = APIRouter(prefix="/debug", tags=["debug"])


@router.patch("/me", response_model=schemas.DebugMeResult)
def patch_my_debug_state(
    patch_in: schemas.DebugMePatch,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_admin)
    update_data = patch_in.dict(exclude_unset=True)

    if "coin" in update_data and update_data["coin"] is not None:
        current_admin.coin = max(update_data["coin"], 0)
    if "xp_point" in update_data and update_data["xp_point"] is not None:
        current_admin.xp_point = max(update_data["xp_point"], 0)
    if "stage" in update_data and update_data["stage"] is not None:
        character.stage = max(update_data["stage"], 1)
    if "character_state" in update_data and update_data["character_state"] is not None:
        character.state = update_data["character_state"]

    db.commit()
    db.refresh(current_admin)
    db.refresh(character)
    return {
        "user": current_admin,
        "character": serialize_my_character(character, current_admin),
    }
