from fastapi.testclient import TestClient
from app.main import app


def test_rate_limiter_exceeded():
    # TestClient without x-skip-rate-limit header
    with TestClient(app) as client:
        # Rapid fire login requests to hit rate limit
        exceeded = False
        for _ in range(25):
            res = client.post(
                "/auth/login",
                data={"username": "user@example.com", "password": "wrong"},
            )
            if res.status_code == 429:
                exceeded = True
                assert "Retry-After" in res.headers
                assert "slow down" in res.json()["detail"].lower()
                break
        assert exceeded, "Expected rate limit 429 to trigger within 25 requests"
