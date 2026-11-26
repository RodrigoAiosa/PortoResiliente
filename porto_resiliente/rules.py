"""Regras de risco, puras e testáveis (sem rede).

Os avisos do IPMA são a fonte oficial. Os limiares baseados na previsão e no
índice de qualidade do ar são HEURÍSTICAS LOCAIS, ajustáveis, e não substituem
os avisos oficiais da Proteção Civil/IPMA.
"""

from __future__ import annotations

from .models import Hazard, Level, ZoneAlert
from .zones import Zone

# Limiares heurísticos (ajustar com a Proteção Civil / dados históricos)
HEAT_T_MAX = {Level.YELLOW: 32.0, Level.ORANGE: 35.0, Level.RED: 38.0}
EAQI = {Level.YELLOW: 60.0, Level.ORANGE: 80.0, Level.RED: 100.0}  # EAQI: "poor" a partir de 60

LEVEL_PT = {Level.GREEN: "verde", Level.YELLOW: "amarelo", Level.ORANGE: "laranja", Level.RED: "vermelho"}

WARNING_TO_HAZARD = {
    "Precipitação": "chuva",
    "Vento": "vento",
    "Tempo Quente": "calor",
    "Tempo Frio": "frio",
    "Trovoada": "trovoada",
    "Nevoeiro": "nevoeiro",
    "Agitação Marítima": "agitacao_maritima",
    "Neve": "neve",
}


def _hazard(
    type_: str, level: Level, reason: str, source: str,
    valid_from: str | None = None, valid_until: str | None = None,
) -> Hazard:
    return Hazard(
        type=type_, level=level.label, reason=reason, source=source,
        valid_from=valid_from, valid_until=valid_until,
    )


def air_label(aqi: float) -> str:
    """Classes do Índice Europeu de Qualidade do Ar (EAQI)."""
    for limit, label in ((20, "Boa"), (40, "Razoável"), (60, "Moderada"), (80, "Fraca"), (100, "Muito fraca")):
        if aqi < limit:
            return label
    return "Extremamente fraca"


def flood_level(forecast: list[dict], rain_warning: Level) -> tuple[Level, str]:
    """Risco de cheias para zonas ribeirinhas.

    Combina o aviso de precipitação do IPMA com a previsão (probabilidade e
    classe de intensidade; assume-se classe 1 fraca, 2 moderada, 3 forte).
    """
    level = Level.GREEN
    reason = ""
    for day in forecast:
        prob = day.get("precip_prob") or 0.0
        cls = day.get("precip_class") or 0
        if prob >= 70 and cls >= 3:
            cand = Level.ORANGE
        elif prob >= 70 and cls >= 2:
            cand = Level.YELLOW
        else:
            continue
        if cand > level:
            level = cand
            reason = (
                f"Previsão de chuva {'forte' if cls >= 3 else 'moderada'} "
                f"({prob:.0f}% de probabilidade) em {day.get('date')}"
            )
    # Aviso e previsão vêm da mesma fonte (IPMA): usa-se o mais alto, sem os somar.
    if rain_warning > level:
        level = rain_warning
        reason = f"Aviso {LEVEL_PT[rain_warning]} de precipitação do IPMA"
    return level, reason


def heat_level(forecast: list[dict]) -> tuple[Level, str]:
    level, reason = Level.GREEN, ""
    for day in forecast:
        t = day.get("t_max")
        if t is None:
            continue
        for lvl in (Level.RED, Level.ORANGE, Level.YELLOW):
            if t >= HEAT_T_MAX[lvl]:
                if lvl > level:
                    level, reason = lvl, f"Máxima prevista de {t:.0f} °C em {day.get('date')}"
                break
    return level, reason


def air_level(aqi: float | None) -> tuple[Level, str]:
    if aqi is None:
        return Level.GREEN, ""
    for lvl in (Level.RED, Level.ORANGE, Level.YELLOW):
        if aqi >= EAQI[lvl]:
            return lvl, f"Índice europeu de qualidade do ar (modelado) = {aqi:.0f}"
    return Level.GREEN, ""


def evaluate_zone(
    zone: Zone,
    warnings: list[dict],
    forecast: list[dict],
    aqi: float | None,
) -> ZoneAlert:
    hazards: list[Hazard] = []
    rain_warning = Level.GREEN
    rain_w: dict | None = None  # aviso de precipitação mais alto (para a janela de validade)

    for w in warnings:
        htype = WARNING_TO_HAZARD.get(w["type_name"])
        if htype is None:
            continue
        if htype == "agitacao_maritima" and not zone.coastal:
            continue
        lvl = Level(w["level"])
        if htype == "chuva":
            if lvl > rain_warning:
                rain_warning, rain_w = lvl, w
            if zone.flood_prone:
                continue  # será reportado como "cheias"
        hazards.append(
            _hazard(
                htype, lvl, f"Aviso {LEVEL_PT[lvl]} do IPMA ({w['type_name']})", "IPMA (aviso)",
                w.get("start"), w.get("end"),
            )
        )

    if zone.flood_prone:
        lvl, reason = flood_level(forecast, rain_warning)
        if lvl > Level.GREEN:
            src = "IPMA (aviso + previsão)" if rain_warning > Level.GREEN else "Heurística local (previsão IPMA)"
            # a janela só se aplica se foi o aviso oficial a definir o nível
            win = rain_w if rain_w is not None and lvl == rain_warning else None
            hazards.append(
                _hazard("cheias", lvl, reason, src, win and win.get("start"), win and win.get("end"))
            )

    lvl, reason = heat_level(forecast)
    if lvl > Level.GREEN and not any(h.type == "calor" and Level[h.level.upper()] >= lvl for h in hazards):
        hazards.append(_hazard("calor", lvl, reason, "Heurística local (previsão IPMA)"))

    lvl, reason = air_level(aqi)
    if lvl > Level.GREEN:
        hazards.append(_hazard("qualidade_ar", lvl, reason, "Open-Meteo/CAMS (modelo)"))

    top = max((Level[h.level.upper()] for h in hazards), default=Level.GREEN)
    hazards.sort(key=lambda h: Level[h.level.upper()], reverse=True)
    return ZoneAlert(
        id=zone.id, name=zone.name, lat=zone.lat, lon=zone.lon, level=top.label, hazards=hazards
    )
