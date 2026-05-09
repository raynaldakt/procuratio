from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer import CustomerProfilePublic, CustomerProfileUpdateSelf, CustomerProfileUpdateStaffNotes
from app.services.customer import get_or_create_profile, update_own_profile, update_staff_notes

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/me/profile", response_model=CustomerProfilePublic)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CustomerProfilePublic:
    profile = get_or_create_profile(db, current_user.id)
    return CustomerProfilePublic.model_validate(profile)


@router.patch("/me/profile", response_model=CustomerProfilePublic)
def patch_my_profile(
    payload: CustomerProfileUpdateSelf,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CustomerProfilePublic:
    updates = payload.model_dump(exclude_unset=True)
    profile = update_own_profile(db, current_user.id, updates)
    return CustomerProfilePublic.model_validate(profile)


@router.get("/{user_id}/profile", response_model=CustomerProfilePublic)
def get_customer_profile(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "staff")),
) -> CustomerProfilePublic:
    try:
        profile = get_or_create_profile(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CustomerProfilePublic.model_validate(profile)


@router.patch("/{user_id}/staff-notes", response_model=CustomerProfilePublic)
def patch_customer_staff_notes(
    user_id: int,
    payload: CustomerProfileUpdateStaffNotes,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "staff")),
) -> CustomerProfilePublic:
    try:
        profile = update_staff_notes(db, user_id, payload.staff_notes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CustomerProfilePublic.model_validate(profile)
