"""Zonas do Porto monitorizadas.

As coordenadas são aproximadas (centro da zona). `flood_prone` e `coastal`
são atributos editáveis: marcam onde cheias e agitação marítima são relevantes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    lat: float
    lon: float
    flood_prone: bool = False
    coastal: bool = False


ZONES: list[Zone] = [
    Zone("ribeira", "Ribeira / Baixa", 41.1406, -8.6130, flood_prone=True),
    Zone("foz", "Foz do Douro", 41.1500, -8.6760, flood_prone=True, coastal=True),
    Zone("campanha", "Campanhã", 41.1495, -8.5850, flood_prone=True),
    Zone("boavista", "Boavista", 41.1580, -8.6430),
    Zone("paranhos", "Paranhos", 41.1790, -8.6000),
]
