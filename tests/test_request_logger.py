class TestRequestLogger:
    async def test_options_requests_are_not_logged(self, client, caplog):
        caplog.set_level("INFO", logger="app.requests")
        caplog.clear()

        res = await client.options(
            "/api/resources",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert res.status_code == 200
        assert not any(
            record.name == "app.requests"
            and getattr(record, "method", None) == "OPTIONS"
            and getattr(record, "path", None) == "/api/resources"
            for record in caplog.records
        )
