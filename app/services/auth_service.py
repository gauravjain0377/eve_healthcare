from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import ConflictException, UnauthorizedException


class AuthService:
    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        """Register a new user after verifying email uniqueness."""
        existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
        if existing_user:
            raise ConflictException(
                detail=f"An account with email '{user_in.email}' already exists.",
                error_code="EMAIL_ALREADY_REGISTERED"
            )

        user = User(
            email=user_in.email.lower(),
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name,
            role=user_in.role.upper() if user_in.role else "PATIENT",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        """Authenticate user by email and password."""
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException(detail="Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedException(detail="Inactive user account")
        return user

    @staticmethod
    def create_token_for_user(user: User) -> dict:
        """Generate JWT access token and return token schema payload."""
        token = create_access_token(
            subject=user.id,
            extra_claims={"email": user.email, "role": user.role}
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user
        }


auth_service = AuthService()
