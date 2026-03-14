import pytest
import json


class TestRegister:
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "name": "Rich",
            "email": "rich@example.com",
            "password": "securepass"
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["user"]["email"] == "rich@example.com"
        assert "access_token" in data

    def test_register_missing_fields(self, client):
        res = client.post("/api/auth/register", json={"email": "rich@example.com"})
        assert res.status_code == 422
        assert "error" in res.get_json()

    def test_register_short_password(self, client):
        res = client.post("/api/auth/register", json={
            "name": "Rich",
            "email": "rich@example.com",
            "password": "short"
        })
        assert res.status_code == 422

    def test_register_duplicate_email(self, client, test_user):
        res = client.post("/api/auth/register", json={
            "name": "Other",
            "email": "test@example.com",
            "password": "password123"
        })
        assert res.status_code == 409

    def test_register_email_normalized_to_lowercase(self, client):
        res = client.post("/api/auth/register", json={
            "name": "Rich",
            "email": "RICH@EXAMPLE.COM",
            "password": "password123"
        })
        assert res.status_code == 201
        assert res.get_json()["user"]["email"] == "rich@example.com"


class TestLogin:
    def test_login_success(self, client, test_user):
        res = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client, test_user):
        res = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        assert res.status_code == 401

    def test_login_unknown_email(self, client):
        res = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123"
        })
        assert res.status_code == 401

    def test_login_missing_fields(self, client):
        res = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert res.status_code == 401
