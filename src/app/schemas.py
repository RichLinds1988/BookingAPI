from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be empty")
        return value

    @field_validator("password")
    @classmethod
    def password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        if value not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")
        return value


class CreateBookingRequest(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime
    guests: int = 1
    notes: Optional[str] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("guests")
    @classmethod
    def guests_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("guests must be at least 1")
        return value

    @model_validator(mode="after")
    def validate_times(self) -> "CreateBookingRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if self.start_time < datetime.now(UTC):
            raise ValueError("start_time cannot be in the past")
        return self


class CreateResourceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: int = 1
    image_url: Optional[str] = None
    tags: Optional[list[str]] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be empty")
        return value


class UpdateResourceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = None
    tags: Optional[list[str]] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str


class ResourceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    capacity: int
    is_active: bool
    image_url: Optional[str] = None
    tags: list[str] = []
    active_booking_count: int = 0


class BookingResponse(BaseModel):
    id: int
    user_id: int
    resource_id: int
    resource_name: Optional[str]
    resource_image_url: Optional[str] = None
    start_time: str
    end_time: str
    notes: Optional[str]
    guests: int
    status: str
    created_at: str


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str

    @field_validator("content_type")
    @classmethod
    def valid_image_type(cls, value: str) -> str:
        allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if value not in allowed:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(allowed))}")
        return value


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_url: str
    key: str
    expires_in: int


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, value: str) -> str:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value

    @field_validator("password")
    @classmethod
    def password_min_length(cls, value: str) -> str:
        if value is not None and len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value
