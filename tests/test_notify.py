import pytest

from porto_resiliente import notify
from porto_resiliente.models import AlertsResponse, Hazard, ZoneAlert


def zone(id_, level, hazards=()):
    return ZoneAlert(id=id_, name=id_.title(), lat=0, lon=0, level=level, hazards=list(hazards))


def resp(zones, **kw):
    return AlertsResponse(updated_at="t", sources=[], notes=[], zones=zones, **kw)


CHEIAS = Hazard(type="cheias", level="orange", reason="Aviso orange de precipitação do IPMA", source="IPMA")


class FakeStore:
    def __init__(self, levels=None):
        self.levels = dict(levels or {})

    async def get_levels(self, ids):
        return {i: self.levels[i] for i in ids if i in self.levels}

    async def set_level(self, zone_id, level):
        self.levels[zone_id] = level


class FakeSender:
    def __init__(self, fail_for=()):
        self.sent, self.fail_for = [], set(fail_for)

    async def send(self, n):
        if n.zone_id in self.fail_for:
            raise RuntimeError("boom")
        self.sent.append(n)


def test_plan_notifies_escalation_to_min_level_only():
    zs = [zone("ribeira", "orange", [CHEIAS]), zone("foz", "yellow"), zone("boavista", "green")]
    out = notify.plan({}, zs, "orange")
    assert [n.zone_id for n in out] == ["ribeira"]
    assert out[0].priority == 4 and "Cheias" in out[0].message and "112" in out[0].message


def test_plan_no_repeat_when_level_unchanged():
    assert notify.plan({"ribeira": "orange"}, [zone("ribeira", "orange")], "orange") == []


def test_plan_escalation_orange_to_red_and_normalisation():
    assert [n.priority for n in notify.plan({"a": "orange"}, [zone("a", "red")])] == [5]
    out = notify.plan({"a": "red"}, [zone("a", "green")])
    assert "normalizada" in out[0].title
    assert notify.plan({"a": "red"}, [zone("a", "orange")]) == []  # continua acima do mínimo


async def test_run_sends_once_then_dedupes():
    store, sender = FakeStore(), FakeSender()
    a = resp([zone("ribeira", "orange", [CHEIAS])])
    r1 = await notify.run(a, store, sender)
    r2 = await notify.run(a, store, sender)
    assert r1["sent"] == ["ribeira"] and r2["sent"] == [] and len(sender.sent) == 1
    r3 = await notify.run(resp([zone("ribeira", "green")]), store, sender)
    assert r3["sent"] == ["ribeira"] and "normalizada" in sender.sent[-1].title


async def test_run_failed_send_keeps_state_for_retry():
    store, sender = FakeStore(), FakeSender(fail_for={"ribeira"})
    a = resp([zone("ribeira", "orange", [CHEIAS])])
    r = await notify.run(a, store, sender)
    assert r["failed"] == ["ribeira"] and "ribeira" not in store.levels
    sender.fail_for.clear()
    assert (await notify.run(a, store, sender))["sent"] == ["ribeira"]


@pytest.mark.parametrize("kw,reason", [({"simulated": True}, "simulation"), ({"degraded": True}, "ipma_unavailable")])
async def test_run_skips_simulation_and_degraded(kw, reason):
    store, sender = FakeStore({"ribeira": "orange"}), FakeSender()
    r = await notify.run(resp([zone("ribeira", "green")], **kw), store, sender)
    assert r == {"status": "skipped", "reason": reason}
    assert sender.sent == [] and store.levels == {"ribeira": "orange"}  # estado intacto


async def test_run_dry_run_without_store():
    r = await notify.run(resp([zone("ribeira", "red", [CHEIAS])]), None, None)
    assert r["status"] == "dry_run" and r["would_notify"] == ["ribeira"]
