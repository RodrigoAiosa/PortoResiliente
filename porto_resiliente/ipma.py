"""Cliente da API aberta do IPMA (https://api.ipma.pt/open-data/).

Estrutura confirmada em 2026-11-26:
- avisos: lista de objetos com `idAreaAviso`, `awarenessTypeName`,
  `awarenessLevelID` (green|yellow|orange|red), `startTime`, `endTime`
- previsão diária (globalIdLocal 1131200 = Porto): `data[]` com
  `forecastDate`, `precipitaProb`, `tMin`, `tMax`, `predWindDir`,
  `classWindSpeed`, `classPrecInt` (opcional)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

BASE = "https://api.ipma.pt/open-data"
PORTO_LOCAL_ID = 1131200
PORTO_AREA = "PTO"
TIMEOUT = httpx.Timeout(8.0)

LEVELS = {"green": 0, "yellow": 1, "orange": 2, "red": 3}


async def fetch_json(client: httpx.AsyncClient, path: str) -> Any:
    r = await client.get(f"{BASE}/{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def parse_warnings(raw: list[dict], now: datetime, area: str = PORTO_AREA) -> list[dict]:
    """Avisos ativos e não-verdes para a área."""
    out = []
    for w in raw:
        if w.get("idAreaAviso") != area:
            continue
        level = LEVELS.get(w.get("awarenessLevelID", "green"), 0)
        if level == 0:
            continue
        try:
            start = datetime.fromisoformat(w["startTime"])
            end = datetime.fromisoformat(w["endTime"])
        except (KeyError, ValueError):
            continue
        if not (start <= now <= end):
            continue
        out.append(
            {
                "type_name": w.get("awarenessTypeName", ""),
                "level": level,
                "start": w["startTime"],
                "end": w["endTime"],
                "text": w.get("text", ""),
            }
        )
    return out


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_forecast(raw: dict, days: int = 2) -> list[dict]:
    """Primeiros `days` dias da previsão, com números convertidos."""
    out = []
    for d in (raw.get("data") or [])[:days]:
        out.append(
            {
                "date": d.get("forecastDate"),
                "precip_prob": _num(d.get("precipitaProb")),
                "precip_class": d.get("classPrecInt"),
                "t_min": _num(d.get("tMin")),
                "t_max": _num(d.get("tMax")),
                "wind_class": d.get("classWindSpeed"),
            }
        )
    return out


async def get_warnings(client: httpx.AsyncClient, now: datetime) -> list[dict]:
    raw = await fetch_json(client, "forecast/warnings/warnings_www.json")
    return parse_warnings(raw, now)


async def get_forecast(client: httpx.AsyncClient) -> list[dict]:
    raw = await fetch_json(client, f"forecast/meteorology/cities/daily/{PORTO_LOCAL_ID}.json")
    return parse_forecast(raw)
