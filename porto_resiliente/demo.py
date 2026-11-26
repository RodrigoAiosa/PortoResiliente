"""Cenários de SIMULAÇÃO para testar o painel e as regras sem esperar por mau tempo.

Nunca devem ser usados para notificações. As respostas marcam `simulated: true`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

SCENARIOS = ("chuva", "calor", "tempestade")


def _w(type_name: str, level: int, now: datetime) -> dict:
    return {
        "type_name": type_name,
        "level": level,
        "start": (now - timedelta(hours=1)).isoformat(timespec="seconds"),
        "end": (now + timedelta(hours=23)).isoformat(timespec="seconds"),
        "text": "SIMULAÇÃO",
    }


def scenario(name: str, now: datetime) -> tuple[list[dict], list[dict], float | None]:
    """Devolve (avisos, previsão, aqi) simulados no formato interno."""
    today = now.date().isoformat()
    if name == "chuva":
        return (
            [_w("Precipitação", 2, now)],
            [{"date": today, "precip_prob": 90.0, "precip_class": 3, "t_min": 10.0, "t_max": 15.0, "wind_class": 2}],
            None,
        )
    if name == "calor":
        return (
            [_w("Tempo Quente", 3, now)],
            [{"date": today, "precip_prob": 0.0, "precip_class": None, "t_min": 22.0, "t_max": 39.0, "wind_class": 1}],
            85.0,
        )
    if name == "tempestade":
        return (
            [_w("Precipitação", 3, now), _w("Vento", 2, now), _w("Agitação Marítima", 3, now), _w("Trovoada", 1, now)],
            [{"date": today, "precip_prob": 100.0, "precip_class": 3, "t_min": 9.0, "t_max": 13.0, "wind_class": 4}],
            None,
        )
    raise ValueError(f"cenário desconhecido: {name}")
