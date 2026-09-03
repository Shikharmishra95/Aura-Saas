from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models.call_log import User, Role, UserRole

async def require_super_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Enforces strict SuperAdmin authorization for Control Tower endpoints.
    Rejects normal hospital admins, receptionists, and doctors with 403 Forbidden.
    """
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    is_owner = (
        "SUPER_ADMIN" in roles 
        or current_user.hospital_id == "super_admin"
    )
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Control Tower requires SuperAdmin privileges."
        )
    return current_user
