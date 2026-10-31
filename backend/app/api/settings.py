from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from app.config import get_settings, Settings
from app.services.db_manager import DatabaseManager
from app.services.settings_store import load_settings, save_settings

router = APIRouter(prefix='/api/settings', tags=['settings'])

class Rate(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=100)
    valid_from: date
    valid_until: date | None = None
    input: float = Field(ge=0, allow_inf_nan=False)
    output: float = Field(ge=0, allow_inf_nan=False)
    cache_read: float = Field(ge=0, allow_inf_nan=False)
    cache_write_5m: float = Field(ge=0, allow_inf_nan=False)
    cache_write_1h: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode='after')
    def valid_dates(self):
        if self.valid_until and self.valid_until < self.valid_from:
            raise ValueError('valid_until must not precede valid_from')
        return self

class AppSettings(BaseModel):
    contract: Literal['unknown', 'api', 'subscription'] = 'unknown'
    monthly_subscription_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    provider: str = Field(default='anthropic', min_length=1, max_length=100)
    rates: list[Rate] = Field(default_factory=list, max_length=100)
    excluded_projects: list[str] = Field(default_factory=list, max_length=100)
    redact_literals: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def valid_values(self):
        if any(not s.strip() or len(s) > 1000 for s in self.excluded_projects + self.redact_literals):
            raise ValueError('Patterns must be non-empty and at most 1000 characters')
        return self


def db_for(settings: Settings = Depends(get_settings)):
    return DatabaseManager(settings.database_path)

@router.get('', response_model=AppSettings)
def get_app_settings(db: DatabaseManager = Depends(db_for)):
    return load_settings(db)

@router.put('', response_model=AppSettings)
def put_app_settings(value: AppSettings, db: DatabaseManager = Depends(db_for)):
    data = value.model_dump(mode='json')
    save_settings(db, data)
    return data
