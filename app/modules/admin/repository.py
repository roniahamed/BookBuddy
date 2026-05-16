"""
Admin module repository.
"""
from sqlalchemy.orm import Session
from app.modules.admin.model import AppConfig


class AdminConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[AppConfig]:
        return self.db.query(AppConfig).order_by(AppConfig.key).all()

    def get_by_key(self, key: str) -> AppConfig | None:
        return self.db.query(AppConfig).filter(AppConfig.key == key).first()

    def set_value(self, key: str, value: str) -> AppConfig:
        config = self.get_by_key(key)
        if config:
            config.value = value
        else:
            config = AppConfig(key=key, value=value)
            self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def seed_defaults(self, defaults: dict[str, tuple[str, str]]) -> None:
        """Seed default configs if they don't exist. defaults = {key: (value, description)}"""
        for key, (value, description) in defaults.items():
            existing = self.get_by_key(key)
            if not existing:
                config = AppConfig(key=key, value=value, description=description)
                self.db.add(config)
        self.db.commit()
