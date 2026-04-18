class TestHealth:
    async def test_health_ok(self, client):
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["dependencies"]["database"] == "ok"
        assert data["dependencies"]["redis"] == "ok"
