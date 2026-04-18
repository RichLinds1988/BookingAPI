
from app.models import Resource


class TestListResources:
    async def test_list_requires_auth(self, client):
        res = await client.get("/api/resources")
        assert res.status_code == 401

    async def test_list_empty(self, client, auth_headers):
        res = await client.get("/api/resources", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    async def test_list_returns_active_resources(self, client, auth_headers, test_resource):
        res = await client.get("/api/resources", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Boardroom A"
        assert data["pagination"]["total"] == 1

    async def test_list_excludes_inactive(self, client, auth_headers, db):
        r = Resource(name="Inactive Room", is_active=False)
        db.add(r)
        await db.flush()

        res = await client.get("/api/resources", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert all(item["is_active"] for item in data["items"])


class TestGetResource:
    async def test_get_existing(self, client, auth_headers, test_resource):
        res = await client.get(f"/api/resources/{test_resource.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Boardroom A"

    async def test_get_not_found(self, client, auth_headers):
        res = await client.get("/api/resources/999", headers=auth_headers)
        assert res.status_code == 404


class TestCreateResource:
    async def test_create_success(self, client, admin_headers):
        res = await client.post(
            "/api/resources",
            headers=admin_headers,
            json={"name": "Meeting Room B", "description": "Small meeting room", "capacity": 4},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Meeting Room B"
        assert data["capacity"] == 4
        assert data["is_active"] is True

    async def test_create_missing_name(self, client, admin_headers):
        res = await client.post(
            "/api/resources",
            headers=admin_headers,
            json={"description": "No name provided"},
        )
        assert res.status_code == 422

    async def test_create_requires_auth(self, client):
        res = await client.post("/api/resources", json={"name": "Room"})
        assert res.status_code == 401

    async def test_create_requires_admin(self, client, auth_headers):
        res = await client.post(
            "/api/resources",
            headers=auth_headers,
            json={"name": "Sneaky Room"},
        )
        assert res.status_code == 403


class TestUpdateResource:
    async def test_update_name(self, client, admin_headers, test_resource):
        res = await client.patch(
            f"/api/resources/{test_resource.id}",
            headers=admin_headers,
            json={"name": "Boardroom B"},
        )
        assert res.status_code == 200
        assert res.json()["name"] == "Boardroom B"

    async def test_deactivate_resource(self, client, admin_headers, test_resource):
        res = await client.patch(
            f"/api/resources/{test_resource.id}",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert res.status_code == 200
        assert res.json()["is_active"] is False

    async def test_update_not_found(self, client, admin_headers):
        res = await client.patch("/api/resources/999", headers=admin_headers, json={"name": "X"})
        assert res.status_code == 404
