"""Qualidade do ar (OPCIONAL).

Usa o Open-Meteo Air Quality (modelo CAMS/Copernicus). ATENÇÃO: são dados
*modelados*, não medições das estações da rede QualAr/APA. Não consegui
confirmar uma API pública estável da QualAr; quando existir, substituir aqui.
Se a chamada falhar, o resto dos alertas continua a funcionar.
"""

from __future__ import annotations

import httpx

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


async def get_european_aqi(client: httpx.AsyncClient, lat: float, lon: float) -> float | None:
    try:
        r = await client.get(
            URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "european_aqi",
                "timezone": "Europe/Lisbon",
            },
            timeout=httpx.Timeout(6.0),
        )
        r.raise_for_status()
        v = r.json().get("current", {}).get("european_aqi")
        return float(v) if v is not None else None
    except (httpx.HTTPError, ValueError, TypeError):
        return None
