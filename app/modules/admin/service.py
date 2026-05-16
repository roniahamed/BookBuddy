"""
Admin config service — cached config access with type conversion.
"""
from sqlalchemy.orm import Session
from app.modules.admin.repository import AdminConfigRepository
from app.modules.admin.schema import AppConfigResponse, AppConfigListResponse, AppConfigUpdateRequest
from fastapi import HTTPException

# Default configs seeded on startup — ALL previously hardcoded values
DEFAULT_CONFIGS: dict[str, tuple[str, str]] = {
    "borrow_reward_borrower_points": ("5", "Points awarded to borrower on confirmed return"),
    "borrow_reward_lender_points": ("10", "Points awarded to lender on confirmed return"),
    "otp_expiry_minutes": ("15", "OTP code validity duration in minutes"),
    "max_borrow_requests_per_user": ("5", "Maximum active borrow requests per user"),
    "default_borrow_duration_days": ("30", "Default borrow period in days"),
    "nearby_radius_km": ("50", "Default nearby search radius in km"),
    "default_language": ("EN", "Default platform language (EN or HE)"),
    "due_date_reminder_days_before": ("2", "Days before due date to send reminder"),
    "overdue_check_interval_hours": ("6", "Hours between overdue book checks"),
}


class AdminConfigService:
    """Provides typed config access. Falls back to defaults if key not in DB."""

    def __init__(self, db: Session):
        self.repo = AdminConfigRepository(db)

    def get(self, key: str, default: str = "") -> str:
        """Get config value as string."""
        config = self.repo.get_by_key(key)
        if config:
            return config.value
        # Fallback to hardcoded defaults
        if key in DEFAULT_CONFIGS:
            return DEFAULT_CONFIGS[key][0]
        return default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get config value as integer."""
        try:
            return int(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get config value as float."""
        try:
            return float(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def list_all(self) -> AppConfigListResponse:
        """List all configs."""
        configs = self.repo.get_all()
        return AppConfigListResponse(
            items=[AppConfigResponse.model_validate(c) for c in configs]
        )

    def get_config(self, key: str) -> AppConfigResponse:
        """Get single config."""
        config = self.repo.get_by_key(key)
        if not config:
            raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
        return AppConfigResponse.model_validate(config)

    def update_config(self, key: str, data: AppConfigUpdateRequest) -> AppConfigResponse:
        """Update a config value."""
        config = self.repo.set_value(key, data.value)
        return AppConfigResponse.model_validate(config)

    def seed_defaults(self) -> None:
        """Seed all default configs on startup."""
        self.repo.seed_defaults(DEFAULT_CONFIGS)
