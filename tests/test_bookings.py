import pytest
from datetime import datetime, timedelta


def make_booking(client, headers, resource_id, start, end, notes=None):
    return client.post("/api/bookings", headers=headers, json={
        "resource_id": resource_id,
        "start_time": start,
        "end_time": end,
        "notes": notes,
    })


class TestCreateBooking:
    def test_create_success(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        res = make_booking(client, auth_headers, test_resource.id, start, end, "Team standup")
        assert res.status_code == 201
        data = res.get_json()
        assert data["status"] == "confirmed"
        assert data["resource_id"] == test_resource.id
        assert data["notes"] == "Team standup"

    def test_create_requires_auth(self, client, test_resource, future_times):
        start, end = future_times
        res = make_booking(client, {}, test_resource.id, start, end)
        assert res.status_code == 401

    def test_create_missing_fields(self, client, auth_headers):
        res = client.post("/api/bookings", headers=auth_headers, json={
            "resource_id": 1
        })
        assert res.status_code == 422

    def test_create_end_before_start(self, client, auth_headers, test_resource):
        start = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        res = make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 422

    def test_create_start_in_past(self, client, auth_headers, test_resource):
        start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        end = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        res = make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 422

    def test_create_conflict(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        make_booking(client, auth_headers, test_resource.id, start, end)
        res = make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 409
        assert "already booked" in res.get_json()["error"]

    def test_back_to_back_allowed(self, client, auth_headers, test_resource):
        base = datetime.now() + timedelta(days=1)
        start1 = base.strftime("%Y-%m-%dT%H:%M:%S")
        end1 = (base + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        start2 = end1
        end2 = (base + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")

        res1 = make_booking(client, auth_headers, test_resource.id, start1, end1)
        res2 = make_booking(client, auth_headers, test_resource.id, start2, end2)
        assert res1.status_code == 201
        assert res2.status_code == 201

    def test_create_inactive_resource(self, client, auth_headers, db, app, future_times):
        with app.app_context():
            from app.models import Resource
            r = Resource(name="Inactive", is_active=False)
            db.session.add(r)
            db.session.commit()
            resource_id = r.id

        start, end = future_times
        res = make_booking(client, auth_headers, resource_id, start, end)
        assert res.status_code == 409

    def test_create_nonexistent_resource(self, client, auth_headers, future_times):
        start, end = future_times
        res = make_booking(client, auth_headers, 9999, start, end)
        assert res.status_code == 404


class TestListBookings:
    def test_list_own_bookings(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        make_booking(client, auth_headers, test_resource.id, start, end)
        res = client.get("/api/bookings", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["items"]) == 1
        assert data["pagination"]["total"] == 1

    def test_list_empty(self, client, auth_headers):
        res = client.get("/api/bookings", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    def test_list_requires_auth(self, client):
        res = client.get("/api/bookings")
        assert res.status_code == 401


class TestGetBooking:
    def test_get_own_booking(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        created = make_booking(client, auth_headers, test_resource.id, start, end).get_json()
        res = client.get(f"/api/bookings/{created['id']}", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["id"] == created["id"]

    def test_get_not_found(self, client, auth_headers):
        res = client.get("/api/bookings/999", headers=auth_headers)
        assert res.status_code == 404

    def test_cannot_get_another_users_booking(self, client, app, db, test_resource, future_times):
        # Create a second user and their booking
        with app.app_context():
            from app.models import User, Booking
            from flask_jwt_extended import create_access_token
            other = User(name="Other", email="other@example.com")
            other.set_password("password123")
            db.session.add(other)
            db.session.commit()

            start_str, end_str = future_times
            fmt = "%Y-%m-%dT%H:%M:%S"
            booking = Booking(
                user_id=other.id,
                resource_id=test_resource.id,
                start_time=datetime.strptime(start_str, fmt) + timedelta(days=5),
                end_time=datetime.strptime(end_str, fmt) + timedelta(days=5),
            )
            db.session.add(booking)
            db.session.commit()
            booking_id = booking.id

            token = create_access_token(identity=str(other.id + 1))  # first user's token
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        res = client.get(f"/api/bookings/{booking_id}", headers=headers)
        assert res.status_code == 404


class TestCancelBooking:
    def test_cancel_success(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        booking = make_booking(client, auth_headers, test_resource.id, start, end).get_json()
        res = client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["status"] == "cancelled"

    def test_cancel_already_cancelled(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        booking = make_booking(client, auth_headers, test_resource.id, start, end).get_json()
        client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        res = client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        assert res.status_code == 409

    def test_cancel_not_found(self, client, auth_headers):
        res = client.delete("/api/bookings/999", headers=auth_headers)
        assert res.status_code == 404

    def test_cancelled_slot_becomes_available(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        booking = make_booking(client, auth_headers, test_resource.id, start, end).get_json()
        client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        # Should now be bookable again
        res = make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 201


class TestAvailability:
    def test_available(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        res = client.get(
            f"/api/bookings/availability/{test_resource.id}?start_time={start}&end_time={end}",
            headers=auth_headers
        )
        assert res.status_code == 200
        assert res.get_json()["available"] is True

    def test_not_available_after_booking(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        make_booking(client, auth_headers, test_resource.id, start, end)
        res = client.get(
            f"/api/bookings/availability/{test_resource.id}?start_time={start}&end_time={end}",
            headers=auth_headers
        )
        assert res.status_code == 200
        assert res.get_json()["available"] is False

    def test_missing_params(self, client, auth_headers, test_resource):
        res = client.get(
            f"/api/bookings/availability/{test_resource.id}",
            headers=auth_headers
        )
        assert res.status_code == 422

    def test_not_found_resource(self, client, auth_headers, future_times):
        start, end = future_times
        res = client.get(
            f"/api/bookings/availability/999?start_time={start}&end_time={end}",
            headers=auth_headers
        )
        assert res.status_code == 404