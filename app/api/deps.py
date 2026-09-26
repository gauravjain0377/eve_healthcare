from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validate bearer token and return authenticated user."""
    if not token:
        raise UnauthorizedException(detail="Not authenticated. Provide a valid Bearer token.")

    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedException(detail="Invalid or expired authentication token.")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(detail="Malformed authentication token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedException(detail="User no longer exists.")

    if not user.is_active:
        raise UnauthorizedException(detail="User account is deactivated.")

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure the authenticated user has ADMIN role."""
    if current_user.role != "ADMIN":
        raise ForbiddenException(detail="Admin privileges required to access this resource.")
    return current_user
