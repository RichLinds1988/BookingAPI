class TestHealth:
    def test_health_ok(self, client, auth_headers):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert data["dependencies"]["database"] == "ok"
        assert data["dependencies"]["redis"] == "ok"
