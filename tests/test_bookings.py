from datetime import datetime, timedelta

from app.models import Booking, Resource, User
from app.utils.auth import create_access_token


async def make_booking(client, headers, resource_id, start, end, notes=None):
    return await client.post(
        "/api/bookings",
        headers=headers,
        json={"resource_id": resource_id, "start_time": start, "end_time": end, "notes": notes},
    )


class TestCreateBooking:
    async def test_create_success(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        res = await make_booking(client, auth_headers, test_resource.id, start, end, "Team standup")
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "confirmed"
        assert data["resource_id"] == test_resource.id
        assert data["notes"] == "Team standup"

    async def test_create_requires_auth(self, client, test_resource, future_times):
        start, end = future_times
        res = await make_booking(client, {}, test_resource.id, start, end)
        assert res.status_code == 401

    async def test_create_missing_fields(self, client, auth_headers):
        res = await client.post("/api/bookings", headers=auth_headers, json={"resource_id": 1})
        assert res.status_code == 422

    async def test_create_end_before_start(self, client, auth_headers, test_resource):
        start = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        res = await make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 422

    async def test_create_start_in_past(self, client, auth_headers, test_resource):
        start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        end = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        res = await make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 422

    async def test_create_conflict(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        await make_booking(client, auth_headers, test_resource.id, start, end)
        res = await make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 409
        assert "already booked" in res.json()["detail"]

    async def test_back_to_back_allowed(self, client, auth_headers, test_resource):
        base = datetime.now() + timedelta(days=1)
        start1 = base.strftime("%Y-%m-%dT%H:%M:%S")
        end1 = (base + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        start2 = end1
        end2 = (base + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")

        res1 = await make_booking(client, auth_headers, test_resource.id, start1, end1)
        res2 = await make_booking(client, auth_headers, test_resource.id, start2, end2)
        assert res1.status_code == 201
        assert res2.status_code == 201

    async def test_create_inactive_resource(self, client, auth_headers, db, future_times):
        r = Resource(name="Inactive", is_active=False)
        db.add(r)
        await db.flush()
        await db.refresh(r)

        start, end = future_times
        res = await make_booking(client, auth_headers, r.id, start, end)
        assert res.status_code == 409

    async def test_create_nonexistent_resource(self, client, auth_headers, future_times):
        start, end = future_times
        res = await make_booking(client, auth_headers, 9999, start, end)
        assert res.status_code == 404


class TestListBookings:
    async def test_list_own_bookings(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        await make_booking(client, auth_headers, test_resource.id, start, end)
        res = await client.get("/api/bookings", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 1
        assert data["pagination"]["total"] == 1

    async def test_list_empty(self, client, auth_headers):
        res = await client.get("/api/bookings", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    async def test_list_requires_auth(self, client):
        res = await client.get("/api/bookings")
        assert res.status_code == 401


class TestGetBooking:
    async def test_get_own_booking(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        created = (await make_booking(client, auth_headers, test_resource.id, start, end)).json()
        res = await client.get(f"/api/bookings/{created['id']}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["id"] == created["id"]

    async def test_get_not_found(self, client, auth_headers):
        res = await client.get("/api/bookings/999", headers=auth_headers)
        assert res.status_code == 404

    async def test_cannot_get_another_users_booking(self, client, db, test_resource, future_times):
        # Create two users: owner and a separate requester
        owner = User(name="Owner", email="owner@example.com")
        owner.set_password("password123")
        requester = User(name="Requester", email="requester@example.com")
        requester.set_password("password123")
        db.add(owner)
        db.add(requester)
        await db.flush()
        await db.refresh(owner)
        await db.refresh(requester)

        start_str, end_str = future_times
        fmt = "%Y-%m-%dT%H:%M:%S"
        booking = Booking(
            user_id=owner.id,
            resource_id=test_resource.id,
            start_time=datetime.strptime(start_str, fmt) + timedelta(days=5),
            end_time=datetime.strptime(end_str, fmt) + timedelta(days=5),
        )
        db.add(booking)
        await db.flush()
        await db.refresh(booking)

        headers = {"Authorization": f"Bearer {create_access_token(requester.id)}"}
        res = await client.get(f"/api/bookings/{booking.id}", headers=headers)
        assert res.status_code == 404


class TestCancelBooking:
    async def test_cancel_success(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        booking = (await make_booking(client, auth_headers, test_resource.id, start, end)).json()
        res = await client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "cancelled"

    async def test_cancel_already_cancelled(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        booking = (await make_booking(client, auth_headers, test_resource.id, start, end)).json()
        await client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        res = await client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        assert res.status_code == 409

    async def test_cancel_not_found(self, client, auth_headers):
        res = await client.delete("/api/bookings/999", headers=auth_headers)
        assert res.status_code == 404

    async def test_cancelled_slot_becomes_available(
        self, client, auth_headers, test_resource, future_times
    ):
        start, end = future_times
        booking = (await make_booking(client, auth_headers, test_resource.id, start, end)).json()
        await client.delete(f"/api/bookings/{booking['id']}", headers=auth_headers)
        res = await make_booking(client, auth_headers, test_resource.id, start, end)
        assert res.status_code == 201


class TestAvailability:
    async def test_available(self, client, auth_headers, test_resource, future_times):
        start, end = future_times
        res = await client.get(
            f"/api/bookings/availability/{test_resource.id}?start_time={start}&end_time={end}",
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["available"] is True

    async def test_not_available_after_booking(
        self, client, auth_headers, test_resource, future_times
    ):
        start, end = future_times
        await make_booking(client, auth_headers, test_resource.id, start, end)
        res = await client.get(
            f"/api/bookings/availability/{test_resource.id}?start_time={start}&end_time={end}",
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["available"] is False

    async def test_missing_params(self, client, auth_headers, test_resource):
        res = await client.get(
            f"/api/bookings/availability/{test_resource.id}", headers=auth_headers
        )
        assert res.status_code == 422

    async def test_not_found_resource(self, client, auth_headers, future_times):
        start, end = future_times
        res = await client.get(
            f"/api/bookings/availability/999?start_time={start}&end_time={end}",
            headers=auth_headers,
        )
        assert res.status_code == 404
