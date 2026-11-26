from fastapi.testclient import TestClient

from api.index import app


import pytest


@pytest.fixture(autouse=True)
def _fresh_cache():
    from porto_resiliente import service

    service.clear_cache()
    yield
    service.clear_cache()


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


def _fake_sources(monkeypatch, calls):
    from porto_resiliente import airquality, ipma

    async def warnings(client, now):
        calls.append("w")
        return []

    async def forecast(client):
        calls.append("f")
        return []

    async def aqi(client, lat, lon):
        return None

    monkeypatch.setattr(ipma, "get_warnings", warnings)
    monkeypatch.setattr(ipma, "get_forecast", forecast)
    monkeypatch.setattr(airquality, "get_european_aqi", aqi)


def test_refresh_bypasses_cdn_but_server_cache_limits_upstream(monkeypatch):
    calls = []
    _fake_sources(monkeypatch, calls)
    c = TestClient(app)
    r1 = c.get("/api/alerts")
    assert "s-maxage" in r1.headers["cache-control"]
    r2 = c.get("/api/alerts?refresh=1")
    assert r2.headers["cache-control"] == "no-store"
    assert calls == ["w", "f"]  # a 2.ª chamada serviu-se da cache de 60 s: o IPMA não foi consultado de novo


def test_refresh_after_ttl_fetches_again(monkeypatch):
    from porto_resiliente import service

    calls = []
    _fake_sources(monkeypatch, calls)
    c = TestClient(app)
    c.get("/api/alerts")
    service._cache = (service._cache[0] - service.CACHE_TTL - 1, service._cache[1])  # expira a cache
    c.get("/api/alerts?refresh=1")
    assert calls == ["w", "f", "w", "f"]


def test_failures_are_not_cached(monkeypatch):
    import httpx

    async def boom(*a, **k):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.AsyncClient, "get", boom)
    c = TestClient(app)
    assert c.get("/api/alerts").json()["degraded"] is True
    monkeypatch.undo()
    calls = []
    _fake_sources(monkeypatch, calls)
    assert c.get("/api/alerts").json()["degraded"] is False  # recuperou logo, sem esperar pelo TTL
    assert calls == ["w", "f"]


def test_cron_notify_ignores_cache(monkeypatch):
    calls = []
    _fake_sources(monkeypatch, calls)
    monkeypatch.setenv("CRON_SECRET", "s" * 20)
    c = TestClient(app)
    c.get("/api/alerts")  # enche a cache
    c.get("/api/cron/notify", headers={"Authorization": "Bearer " + "s" * 20})
    assert calls == ["w", "f", "w", "f"]
