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


class ZoneAlert(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    level: str
    hazards: list[Hazard]


class AlertsResponse(BaseModel):
    updated_at: str
    sources: list[str]
    notes: list[str]
    zones: list[ZoneAlert]
