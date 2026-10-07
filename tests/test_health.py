"""
The health check against a real and an unreachable database. Database-backed.
"""

from basic_api import main
from tests.test_smoke import bare_client


async def test_health_is_200_when_the_database_answers(client):
    async with bare_client() as bare:
        response = await bare.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": main.SERVICE_NAME,
        "database": "ok",
    }


async def test_health_is_503_when_the_database_does_not(client, monkeypatch):
    async def down() -> bool:
        return False

    monkeypatch.setattr(main, "ping", down)
    async with bare_client() as bare:
        response = await bare.get("/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"


async def test_root_reports_the_configured_version():
    from basic_api.config import APP_VERSION

    async with bare_client() as bare:
        response = await bare.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == APP_VERSION
