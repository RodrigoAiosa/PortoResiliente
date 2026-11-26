from __future__ import annotations

import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from . import airquality, demo, ipma
from .models import AirQuality, AlertsResponse, DayForecast
from .rules import air_label, evaluate_zone
from .zones import ZONES

TZ = ZoneInfo("Europe/Lisbon")
DISCLAIMER = "Informação indicativa. Em emergência ligue 112 e siga a Proteção Civil."


def _now_local() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)  # IPMA usa hora local sem offset


# Cache curto por instância: o botão «Atualizar» pode ser clicado por qualquer pessoa,
# por isso limita-se a frequência real de chamadas ao IPMA (~1 por minuto por instância).
CACHE_TTL = 60.0
_cache: tuple[float, AlertsResponse] | None = None


def clear_cache() -> None:
    global _cache
    _cache = None


def _context(forecast: list[dict], aqi: float | None) -> tuple[DayForecast | None, AirQuality | None]:
    """Previsão do primeiro dia e qualidade do ar, para mostrar nos detalhes de cada zona."""
    day = None
    if forecast:
        f = forecast[0]
        day = DayForecast(
            date=f.get("date"), precip_prob=f.get("precip_prob"), t_min=f.get("t_min"), t_max=f.get("t_max"),
            precip_class=f.get("precip_class"), wind_class=f.get("wind_class"),
        )
    air = AirQuality(eaqi=aqi, label=air_label(aqi)) if aqi is not None else None
    return day, air


async def build_alerts(demo_scenario: str | None = None, use_cache: bool = True) -> AlertsResponse:
    global _cache
    now = _now_local()

    if demo_scenario:
        warnings, forecast, aqi = demo.scenario(demo_scenario, now)
        day, air = _context(forecast, aqi)
        return AlertsResponse(
            simulated=True,
            forecast=day,
            air_quality=air,
            updated_at=datetime.now(TZ).isoformat(timespec="seconds"),
            sources=["SIMULAÇÃO (dados fictícios)"],
            notes=[f"Cenário simulado «{demo_scenario}». Não são alertas reais.", DISCLAIMER],
            zones=[evaluate_zone(z, warnings, forecast, aqi) for z in ZONES],
        )

    if use_cache and _cache is not None and time.monotonic() - _cache[0] < CACHE_TTL:
        return _cache[1]

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
    day, air = _context(forecast, aqi)
    result = AlertsResponse(
        forecast=day,
        air_quality=air,
        degraded=isinstance(warnings_r, Exception) or isinstance(forecast_r, Exception),
        updated_at=datetime.now(TZ).isoformat(timespec="seconds"),
        sources=sources,
        notes=notes + [DISCLAIMER],
        zones=zones,
    )
    if not result.degraded:  # nunca guarda resultados de falha
        _cache = (time.monotonic(), result)
    return result
