from datetime import datetime, timezone
from typing import List, Optional

import bcrypt
from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("user", "admin", name="user_role"), default="user", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    bookings: Mapped[List["Booking"]] = relationship(
        "Booking", back_populates="user", lazy="selectin"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role}


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    capacity: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    bookings: Mapped[List["Booking"]] = relationship(
        "Booking", back_populates="resource", lazy="selectin"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capacity": self.capacity,
            "is_active": self.is_active,
        }


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    guests: Mapped[int] = mapped_column(default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("confirmed", "cancelled", "pending", name="booking_status"), default="confirmed"
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_bookings_resource_time", "resource_id", "start_time", "end_time"),)

    user: Mapped["User"] = relationship("User", back_populates="bookings")
    resource: Mapped["Resource"] = relationship("Resource", back_populates="bookings")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "resource_name": self.resource.name if self.resource else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "notes": self.notes,
            "guests": self.guests,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
