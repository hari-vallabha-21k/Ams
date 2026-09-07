from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models import User
from app.security import create_access_token, hash_password, verify_password
from app.services import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalars(select(User).where(User.email == email.lower().strip())).first()
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return user


def _token_response(user: User) -> schemas.TokenResponse:
    return schemas.TokenResponse(
        access_token=create_access_token(str(user.id), user.role, {"email": user.email}),
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = _authenticate(db, payload.email, payload.password)
    audit.record(db, user=user, action="LOGIN", entity="user", entity_id=user.id, ip_address=client_ip(request))
    db.commit()
    return _token_response(user)


@router.post("/token", response_model=schemas.TokenResponse, include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow, used by the interactive API docs."""
    return _token_response(_authenticate(db, form.username, form.password))


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: schemas.PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    audit.record(db, user=user, action="CHANGE_PASSWORD", entity="user", entity_id=user.id, ip_address=client_ip(request))
    db.commit()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Stateless JWT logout: the client discards the token; we keep the trail."""
    audit.record(db, user=user, action="LOGOUT", entity="user", entity_id=user.id, ip_address=client_ip(request))
    db.commit()
