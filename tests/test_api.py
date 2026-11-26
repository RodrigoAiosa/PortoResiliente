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


def test_demo_chuva_is_flagged_and_raises_flood_zones():
    r = TestClient(app).get("/api/alerts?demo=chuva")
    body = r.json()
    assert r.status_code == 200 and body["simulated"] is True
    assert r.headers["cache-control"] == "no-store"
    by_id = {z["id"]: z for z in body["zones"]}
    assert by_id["ribeira"]["level"] == "orange"
    assert any(h["type"] == "cheias" for h in by_id["ribeira"]["hazards"])
    assert by_id["boavista"]["level"] == "orange"  # chuva genérica
    assert any("simulado" in n.lower() for n in body["notes"])


def test_demo_tempestade_reaches_red_and_coastal_only_sea():
    body = TestClient(app).get("/api/alerts?demo=tempestade").json()
    by_id = {z["id"]: z for z in body["zones"]}
    assert by_id["foz"]["level"] == "red"
    assert "agitacao_maritima" in {h["type"] for h in by_id["foz"]["hazards"]}
    assert "agitacao_maritima" not in {h["type"] for h in by_id["paranhos"]["hazards"]}


def test_demo_calor_has_heat_and_air():
    body = TestClient(app).get("/api/alerts?demo=calor").json()
    types = {h["type"] for h in body["zones"][3]["hazards"]}
    assert {"calor", "qualidade_ar"} <= types


def test_demo_rejects_unknown_scenario():
    assert TestClient(app).get("/api/alerts?demo=xyz").status_code == 422


def test_cron_notify_requires_secret(monkeypatch):
    c = TestClient(app)
    monkeypatch.delenv("CRON_SECRET", raising=False)
    assert c.get("/api/cron/notify").status_code == 401
    assert c.get("/api/cron/notify", headers={"Authorization": "Bearer "}).status_code == 401
    monkeypatch.setenv("CRON_SECRET", "s" * 20)
    assert c.get("/api/cron/notify").status_code == 401
    assert c.get("/api/cron/notify", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_cron_notify_with_secret_degraded_skips(monkeypatch):
    import httpx

    async def boom(*a, **k):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.AsyncClient, "get", boom)
    monkeypatch.setenv("CRON_SECRET", "s" * 20)
    r = TestClient(app).get("/api/cron/notify", headers={"Authorization": "Bearer " + "s" * 20})
    assert r.status_code == 200 and r.json() == {"status": "skipped", "reason": "ipma_unavailable"}
