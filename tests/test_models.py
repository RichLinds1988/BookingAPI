from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Booking, Resource, User


class TestUserModel:
    def test_password_hashing(self):
        user = User(name="Rich", email="rich@example.com")
        user.set_password("mypassword")
        assert user.password_hash != "mypassword"  # noqa: S105
        assert user.check_password("mypassword") is True
        assert user.check_password("wrongpassword") is False

    async def test_to_dict(self, db):
        user = User(name="Rich", email="rich@example.com")
        user.set_password("password")
        db.add(user)
        await db.flush()
        await db.refresh(user)
        d = user.to_dict()
        assert d["email"] == "rich@example.com"
        assert d["name"] == "Rich"
        assert "password_hash" not in d

    async def test_unique_email_constraint(self, db):
        u1 = User(name="Rich", email="same@example.com")
        u1.set_password("pass1234")
        u2 = User(name="Other", email="same@example.com")
        u2.set_password("pass1234")
        db.add(u1)
        await db.flush()
        db.add(u2)
        with pytest.raises(IntegrityError):
            await db.flush()


class TestResourceModel:
    async def test_defaults(self, db):
        r = Resource(name="Room A")
        db.add(r)
        await db.flush()
        await db.refresh(r)
        assert r.is_active is True
        assert r.capacity == 1

    async def test_to_dict(self, db):
        r = Resource(name="Room A", description="Nice room", capacity=5)
        db.add(r)
        await db.flush()
        await db.refresh(r)
        d = r.to_dict()
        assert d["name"] == "Room A"
        assert d["capacity"] == 5
        assert d["is_active"] is True


class TestBookingModel:
    async def test_to_dict(self, db):
        user = User(name="Rich", email="rich@example.com")
        user.set_password("password123")
        resource = Resource(name="Room A")
        db.add(user)
        db.add(resource)
        await db.flush()

        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=1)
        booking = Booking(
            user_id=user.id,
            resource_id=resource.id,
            start_time=start,
            end_time=end,
            notes="Test meeting",
        )
        db.add(booking)
        await db.flush()

        # Load via query so selectin relationship loading fires
        result = await db.execute(select(Booking).filter_by(id=booking.id))
        loaded = result.scalar_one()

        d = loaded.to_dict()
        assert d["status"] == "confirmed"
        assert d["notes"] == "Test meeting"
        assert d["resource_name"] == "Room A"
        assert "start_time" in d
        assert "end_time" in d