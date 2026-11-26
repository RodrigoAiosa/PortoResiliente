from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel


class Level(IntEnum):
    GREEN = 0
    YELLOW = 1
    ORANGE = 2
    RED = 3

    @property
    def label(self) -> str:
        return self.name.lower()


class Hazard(BaseModel):
    type: str  # cheias, calor, vento, qualidade_ar, ...
    level: str  # green | yellow | orange | red
    reason: str
    source: str  # IPMA (aviso), IPMA (previsão), heurística local, ...
    # janela de validade do aviso oficial (hora de Lisboa, sem fuso); None se não aplicável
    valid_from: str | None = None
    valid_until: str | None = None


class DayForecast(BaseModel):
    """Previsão do IPMA para o Porto (a mesma para toda a cidade)."""

    date: str | None = None
    precip_prob: float | None = None  # %
    precip_class: int | None = None  # classe IPMA de intensidade (1 fraca, 2 moderada, 3 forte)
    t_min: float | None = None
    t_max: float | None = None
    wind_class: int | None = None  # classe IPMA de vento (1 fraco ... 4 muito forte)


class AirQuality(BaseModel):
    eaqi: float
    label: str
    modeled: bool = True  # modelo CAMS, não medição de estação


class ZoneAlert(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    level: str
    hazards: list[Hazard]


class AlertsResponse(BaseModel):
    simulated: bool = False
    # True se avisos ou previsão do IPMA falharam: os "verdes" não são fiáveis
    degraded: bool = False
    updated_at: str
    sources: list[str]
    notes: list[str]
    forecast: DayForecast | None = None
    air_quality: AirQuality | None = None
    zones: list[ZoneAlert]
