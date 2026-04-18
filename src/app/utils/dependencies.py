from fastapi import Depends, HTTPException

from app.models import User
from app.utils.auth import get_current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that restricts a route to admin users only. Returns 403 if not admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
