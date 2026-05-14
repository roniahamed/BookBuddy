from fastapi import Depends, HTTPException, status
from typing import List
from app.core.exceptions import PermissionDeniedException

def has_role(allowed_roles: List[str]):
    def role_checker(user: dict = Depends(lambda r: r.state.user)):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        user_role = user.get("role")
        if user_role not in allowed_roles:
            raise PermissionDeniedException()
        
        return user
    return role_checker

# Usage example:
# @router.get("/admin")
# async def admin_only(user = Depends(has_role(["admin"]))):
#     ...
