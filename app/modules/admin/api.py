"""
Admin module API — manage application configuration.
Only accessible by admin users.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.admin.service import AdminConfigService
from app.modules.admin.schema import AppConfigResponse, AppConfigUpdateRequest, AppConfigListResponse

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: only admin users can access admin endpoints."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get(
    "/config",
    response_model=AppConfigListResponse,
    summary="List all configurations",
    description=(
        "Get all admin-configurable settings: borrow points, OTP expiry, "
        "nearby radius, etc. Only accessible by admin users."
    ),
)
async def list_configs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminConfigService(db)
    return service.list_all()


@router.get(
    "/config/{key}",
    response_model=AppConfigResponse,
    summary="Get a configuration",
    description="Get a single configuration value by key.",
    responses={404: {"description": "Config key not found"}},
)
async def get_config(
    key: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminConfigService(db)
    return service.get_config(key)


@router.put(
    "/config/{key}",
    response_model=AppConfigResponse,
    summary="Update a configuration",
    description=(
        "Update a configuration value. Examples:\n"
        "- `borrow_reward_borrower_points` = 5 (points for borrower on confirmed return)\n"
        "- `borrow_reward_lender_points` = 10 (points for lender)\n"
        "- `otp_expiry_minutes` = 15\n"
        "- `nearby_radius_km` = 50\n"
        "- `default_borrow_duration_days` = 30"
    ),
)
async def update_config(
    key: str,
    data: AppConfigUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminConfigService(db)
    return service.update_config(key, data)
