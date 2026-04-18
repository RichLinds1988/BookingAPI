

class TestRegister:
    async def test_register_success(self, client):
        res = await client.post(
            "/api/auth/register",
            json={"name": "Rich", "email": "rich@example.com", "password": "securepass"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["user"]["email"] == "rich@example.com"
        assert "access_token" in data

    async def test_register_missing_fields(self, client):
        res = await client.post("/api/auth/register", json={"email": "rich@example.com"})
        assert res.status_code == 422

    async def test_register_short_password(self, client):
        res = await client.post(
            "/api/auth/register",
            json={"name": "Rich", "email": "rich@example.com", "password": "short"},
        )
        assert res.status_code == 422

    async def test_register_duplicate_email(self, client, test_user):
        res = await client.post(
            "/api/auth/register",
            json={"name": "Other", "email": "test@example.com", "password": "password123"},
        )
        assert res.status_code == 409

    async def test_register_email_normalized_to_lowercase(self, client):
        res = await client.post(
            "/api/auth/register",
            json={"name": "Rich", "email": "RICH@EXAMPLE.COM", "password": "password123"},
        )
        assert res.status_code == 201
        assert res.json()["user"]["email"] == "rich@example.com"


class TestLogin:
    async def test_login_success(self, client, test_user):
        res = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    async def test_login_wrong_password(self, client, test_user):
        res = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert res.status_code == 401

    async def test_login_unknown_email(self, client):
        res = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert res.status_code == 401

    async def test_login_missing_fields(self, client):
        # Pydantic validates required fields before the handler runs
        res = await client.post("/api/auth/login", json={"email": "test@example.com"})
        assert res.status_code == 422

    async def test_login_returns_refresh_token(self, client, test_user):
        res = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert res.status_code == 200
        assert "refresh_token" in res.json()


class TestUpdateRole:
    async def test_promote_user_to_admin(self, client, admin_headers, test_user):
        res = await client.patch(
            f"/api/auth/users/{test_user.id}/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "admin"

    async def test_demote_user(self, client, admin_headers, db):
        from app.models import User

        other_admin = User(name="Other Admin", email="other@example.com", role="admin")
        other_admin.set_password("password123")
        db.add(other_admin)
        await db.flush()
        await db.refresh(other_admin)

        res = await client.patch(
            f"/api/auth/users/{other_admin.id}/role",
            headers=admin_headers,
            json={"role": "user"},
        )
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "user"

    async def test_requires_admin(self, client, auth_headers, test_user):
        res = await client.patch(
            f"/api/auth/users/{test_user.id}/role",
            headers=auth_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 403

    async def test_cannot_demote_self(self, client, admin_headers, admin_user):
        res = await client.patch(
            f"/api/auth/users/{admin_user.id}/role",
            headers=admin_headers,
            json={"role": "user"},
        )
        assert res.status_code == 400

    async def test_user_not_found(self, client, admin_headers):
        res = await client.patch(
            "/api/auth/users/9999/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 404


class TestRefresh:
    async def test_refresh_returns_new_access_token(self, client, refresh_headers):
        res = await client.post("/api/auth/refresh", headers=refresh_headers)
        assert res.status_code == 200
        assert "access_token" in res.json()

    async def test_refresh_fails_with_access_token(self, client, auth_headers):
        # Access tokens have type="access"; the refresh endpoint expects type="refresh"
        res = await client.post("/api/auth/refresh", headers=auth_headers)
        assert res.status_code == 401

    async def test_refresh_fails_without_token(self, client):
        res = await client.post("/api/auth/refresh")
        assert res.status_code == 401
