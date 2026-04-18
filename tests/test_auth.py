

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
