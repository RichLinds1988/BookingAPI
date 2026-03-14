import pytest
from app.models import User, Resource, Booking
from datetime import datetime, timedelta


class TestUserModel:
    def test_password_hashing(self, app, db):
        with app.app_context():
            user = User(name="Rich", email="rich@example.com")
            user.set_password("mypassword")
            assert user.password_hash != "mypassword"
            assert user.check_password("mypassword") is True
            assert user.check_password("wrongpassword") is False

    def test_to_dict(self, app, db):
        with app.app_context():
            user = User(name="Rich", email="rich@example.com")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
            d = user.to_dict()
            assert d["email"] == "rich@example.com"
            assert d["name"] == "Rich"
            assert "password_hash" not in d

    def test_unique_email_constraint(self, app, db):
        with app.app_context():
            u1 = User(name="Rich", email="same@example.com")
            u1.set_password("pass1234")
            u2 = User(name="Other", email="same@example.com")
            u2.set_password("pass1234")
            db.session.add(u1)
            db.session.commit()
            db.session.add(u2)
            with pytest.raises(Exception):
                db.session.commit()


class TestResourceModel:
    def test_defaults(self, app, db):
        with app.app_context():
            r = Resource(name="Room A")
            db.session.add(r)
            db.session.commit()
            assert r.is_active is True
            assert r.capacity == 1

    def test_to_dict(self, app, db):
        with app.app_context():
            r = Resource(name="Room A", description="Nice room", capacity=5)
            db.session.add(r)
            db.session.commit()
            d = r.to_dict()
            assert d["name"] == "Room A"
            assert d["capacity"] == 5
            assert d["is_active"] is True


class TestBookingModel:
    def test_to_dict(self, app, db):
        with app.app_context():
            user = User(name="Rich", email="rich@example.com")
            user.set_password("password123")
            resource = Resource(name="Room A")
            db.session.add_all([user, resource])
            db.session.commit()

            start = datetime.now() + timedelta(days=1)
            end = start + timedelta(hours=1)
            booking = Booking(
                user_id=user.id,
                resource_id=resource.id,
                start_time=start,
                end_time=end,
                notes="Test meeting",
            )
            db.session.add(booking)
            db.session.commit()

            d = booking.to_dict()
            assert d["status"] == "confirmed"
            assert d["notes"] == "Test meeting"
            assert d["resource_name"] == "Room A"
            assert "start_time" in d
            assert "end_time" in d
