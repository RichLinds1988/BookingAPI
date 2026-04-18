from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")
        return v


class CreateBookingRequest(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime
    guests: int = 1
    notes: Optional[str] = None

    @field_validator("guests")
    @classmethod
    def guests_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("guests must be at least 1")
        return v

    @model_validator(mode="after")
    def validate_times(self) -> "CreateBookingRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if self.start_time < datetime.now():
            raise ValueError("start_time cannot be in the past")
        return self


class CreateResourceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: int = 1

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class UpdateResourceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None
