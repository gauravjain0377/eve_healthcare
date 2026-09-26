from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limiter import rate_limit
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import auth_service
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new patient or admin user with unique email address."
)
def signup(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _ = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    user = auth_service.register_user(db, user_in)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and obtain JWT token",
    description="Validates email and password, returning a signed JWT Bearer access token."
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
    _ = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    user = auth_service.authenticate_user(db, credentials.email, credentials.password)
    return auth_service.create_token_for_user(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns profile information for the currently authenticated user."
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
