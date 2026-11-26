from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from . import airquality, demo, ipma
from .models import AlertsResponse
from .rules import evaluate_zone
from .zones import ZONES

TZ = ZoneInfo("Europe/Lisbon")
DISCLAIMER = "Informação indicativa. Em emergência ligue 112 e siga a Proteção Civil."


def _now_local() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)  # IPMA usa hora local sem offset


async def build_alerts(demo_scenario: str | None = None) -> AlertsResponse:
    now = _now_local()

    if demo_scenario:
        warnings, forecast, aqi = demo.scenario(demo_scenario, now)
        return AlertsResponse(
            simulated=True,
            updated_at=datetime.now(TZ).isoformat(timespec="seconds"),
            sources=["SIMULAÇÃO (dados fictícios)"],
            notes=[f"Cenário simulado «{demo_scenario}». Não são alertas reais.", DISCLAIMER],
            zones=[evaluate_zone(z, warnings, forecast, aqi) for z in ZONES],
        )

    notes: list[str] = []
    sources = ["IPMA (avisos e previsão)"]

    async with httpx.AsyncClient() as client:
        warnings_r, forecast_r, aqi_r = await asyncio.gather(
            ipma.get_warnings(client, now),
            ipma.get_forecast(client),
            airquality.get_european_aqi(client, ZONES[0].lat, ZONES[0].lon),
            return_exceptions=True,
        )

    warnings = warnings_r if not isinstance(warnings_r, Exception) else []
    forecast = forecast_r if not isinstance(forecast_r, Exception) else []
    aqi = aqi_r if not isinstance(aqi_r, Exception) else None

    if isinstance(warnings_r, Exception):
        notes.append("Avisos do IPMA indisponíveis neste momento.")
    if isinstance(forecast_r, Exception):
        notes.append("Previsão do IPMA indisponível neste momento.")
    if aqi is None:
        notes.append("Qualidade do ar indisponível (fonte opcional).")
    else:
        sources.append("Open-Meteo/CAMS (qualidade do ar, modelado)")

    zones = [evaluate_zone(z, warnings, forecast, aqi) for z in ZONES]
    return AlertsResponse(
        degraded=isinstance(warnings_r, Exception) or isinstance(forecast_r, Exception),
        updated_at=datetime.now(TZ).isoformat(timespec="seconds"),
        sources=sources,
        notes=notes + [DISCLAIMER],
        zones=zones,
    )
