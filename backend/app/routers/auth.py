from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, LoginRequest, UserCreate, UserOut
from app.utils.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
        is_admin=data.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, user_id=user.id, name=user.name, is_admin=user.is_admin)


@router.post("/desktop-auto-login", response_model=Token)
def desktop_auto_login(request: Request, db: Session = Depends(get_db)):
    """Desktop-only: auto-login without credentials. Localhost access only."""
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="Not allowed")
    # Get the first active admin, or create one on first launch
    user = db.query(User).filter(User.is_active == True, User.is_admin == True).first()
    if not user:
        user = User(
            email="admin@tallyinsights.local",
            name="Admin",
            hashed_password=hash_password("desktop-local-only"),
            is_admin=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, user_id=user.id, name=user.name, is_admin=user.is_admin)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(__import__("app.utils.auth", fromlist=["get_current_user"]).get_current_user)):
    return current_user
