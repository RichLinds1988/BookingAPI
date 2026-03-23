import pytest


class TestListResources:
    def test_list_requires_auth(self, client):
        res = client.get("/api/resources")
        assert res.status_code == 401

    def test_list_empty(self, client, auth_headers):
        res = client.get("/api/resources", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    def test_list_returns_active_resources(self, client, auth_headers, test_resource):
        res = client.get("/api/resources", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Boardroom A"
        assert data["pagination"]["total"] == 1

    def test_list_excludes_inactive(self, client, auth_headers, db, app):
        with app.app_context():
            from app.models import Resource
            r = Resource(name="Inactive Room", is_active=False)
            db.session.add(r)
            db.session.commit()

        res = client.get("/api/resources", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert all(r["is_active"] for r in data["items"])


class TestGetResource:
    def test_get_existing(self, client, auth_headers, test_resource):
        res = client.get(f"/api/resources/{test_resource.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["name"] == "Boardroom A"

    def test_get_not_found(self, client, auth_headers):
        res = client.get("/api/resources/999", headers=auth_headers)
        assert res.status_code == 404


class TestCreateResource:
    def test_create_success(self, client, admin_headers):
        res = client.post("/api/resources", headers=admin_headers, json={
            "name": "Meeting Room B",
            "description": "Small meeting room",
            "capacity": 4
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Meeting Room B"
        assert data["capacity"] == 4
        assert data["is_active"] is True

    def test_create_missing_name(self, client, admin_headers):
        res = client.post("/api/resources", headers=admin_headers, json={
            "description": "No name provided"
        })
        assert res.status_code == 422

    def test_create_requires_auth(self, client):
        res = client.post("/api/resources", json={"name": "Room"})
        assert res.status_code == 401


class TestUpdateResource:
    def test_update_name(self, client, admin_headers, test_resource):
        res = client.patch(
            f"/api/resources/{test_resource.id}",
            headers=admin_headers,
            json={"name": "Boardroom B"}
        )
        assert res.status_code == 200
        assert res.get_json()["name"] == "Boardroom B"

    def test_deactivate_resource(self, client, admin_headers, test_resource):
        res = client.patch(
            f"/api/resources/{test_resource.id}",
            headers=admin_headers,
            json={"is_active": False}
        )
        assert res.status_code == 200
        assert res.get_json()["is_active"] is False

    def test_update_not_found(self, client, admin_headers):
        res = client.patch("/api/resources/999", headers=admin_headers, json={"name": "X"})
        assert res.status_code == 404
