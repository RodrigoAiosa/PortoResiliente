from fastapi.testclient import TestClient

from api.index import app


def test_health():
    r = TestClient(app).get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_alerts_degrades_gracefully(monkeypatch):
    """Sem rede, a API responde 200 com notas de indisponibilidade e zonas verdes."""
    import httpx

    async def boom(*a, **k):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.AsyncClient, "get", boom)
    r = TestClient(app).get("/api/alerts")
    assert r.status_code == 200
    body = r.json()
    assert len(body["zones"]) == 5
    assert all(z["level"] == "green" for z in body["zones"])
    assert any("indisponíveis" in n or "indisponível" in n for n in body["notes"])
    assert "s-maxage" in r.headers["cache-control"]
