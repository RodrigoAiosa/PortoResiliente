"""Notificações por zona (push via ntfy.sh), com deteção de mudança de nível.

- Cada zona tem o seu tópico ntfy: `{NTFY_TOPIC_PREFIX}-{zone.id}`. Tópicos do ntfy.sh
  são PÚBLICOS: use um prefixo longo e difícil de adivinhar.
- Só notifica quando o nível SOBE até ao mínimo configurado (NOTIFY_MIN_LEVEL, por
  omissão "orange") ou quando uma zona NORMALIZA (desce abaixo do mínimo).
- O último nível de cada zona fica guardado (Upstash Redis). Sem armazenamento
  configurado, corre em modo de ensaio: calcula mas não envia (não há como evitar repetições).
- Nunca envia nem altera estado se os dados do IPMA estiverem indisponíveis (`degraded`)
  ou se a resposta for uma simulação.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx

from .models import AlertsResponse, ZoneAlert

ORDER = {"green": 0, "yellow": 1, "orange": 2, "red": 3}
LEVEL_PT = {"green": "Sem alertas", "yellow": "Atenção", "orange": "Risco elevado", "red": "Risco muito elevado"}
HAZARD_PT = {
    "cheias": "Cheias", "chuva": "Chuva", "calor": "Calor", "frio": "Frio", "vento": "Vento",
    "trovoada": "Trovoada", "nevoeiro": "Nevoeiro", "agitacao_maritima": "Agitação marítima",
    "qualidade_ar": "Qualidade do ar", "neve": "Neve",
}
PRIORITY = {"green": 2, "yellow": 3, "orange": 4, "red": 5}
TAGS = {"green": ["white_check_mark"], "yellow": ["warning"], "orange": ["warning"], "red": ["rotating_light"]}


@dataclass(frozen=True)
class Notification:
    zone_id: str
    new_level: str
    title: str
    message: str
    priority: int
    tags: list[str]


class Store(Protocol):
    async def get_levels(self, zone_ids: list[str]) -> dict[str, str]: ...
    async def set_level(self, zone_id: str, level: str) -> None: ...


class Sender(Protocol):
    async def send(self, n: Notification) -> None: ...


def plan(prev: dict[str, str], zones: list[ZoneAlert], min_level: str = "orange") -> list[Notification]:
    """Decide quem notificar. Função pura."""
    floor = ORDER[min_level]
    out: list[Notification] = []
    for z in zones:
        new = ORDER[z.level]
        old = ORDER.get(prev.get(z.id, "green"), 0)
        if new > old and new >= floor:
            lines = [f"• {HAZARD_PT.get(h.type, h.type)}: {h.reason}" for h in z.hazards]
            msg = "\n".join(lines) + "\nInformação indicativa. Em emergência ligue 112."
            out.append(Notification(z.id, z.level, f"{z.name}: {LEVEL_PT[z.level]}", msg, PRIORITY[z.level], TAGS[z.level]))
        elif new < old and old >= floor and new < floor:
            out.append(
                Notification(
                    z.id, z.level, f"{z.name}: situação normalizada",
                    f"O nível desceu para «{LEVEL_PT[z.level]}».", PRIORITY["green"], TAGS["green"],
                )
            )
    return out


async def run(alerts: AlertsResponse, store: Store | None, sender: Sender | None, min_level: str = "orange") -> dict:
    if alerts.simulated:
        return {"status": "skipped", "reason": "simulation"}
    if alerts.degraded:
        return {"status": "skipped", "reason": "ipma_unavailable"}

    ids = [z.id for z in alerts.zones]
    if store is None or sender is None:
        planned = plan({}, alerts.zones, min_level)
        return {"status": "dry_run", "reason": "store_or_sender_not_configured",
                "would_notify": [n.zone_id for n in planned]}

    prev = await store.get_levels(ids)
    planned = plan(prev, alerts.zones, min_level)
    sent: list[str] = []
    failed: list[str] = []
    notified = {n.zone_id: n for n in planned}

    for z in alerts.zones:
        n = notified.get(z.id)
        if n is not None:
            try:
                await sender.send(n)
                sent.append(z.id)
            except Exception:  # não atualiza o estado: tenta de novo na próxima execução
                failed.append(z.id)
                continue
        if prev.get(z.id) != z.level:
            await store.set_level(z.id, z.level)
    return {"status": "ok", "sent": sent, "failed": failed}


# --- Implementações concretas -------------------------------------------------


class UpstashStore:
    """Upstash Redis via REST (Marketplace da Vercel)."""

    def __init__(self, url: str, token: str) -> None:
        self.url, self.token = url.rstrip("/"), token

    @classmethod
    def from_env(cls) -> "UpstashStore | None":
        url = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("KV_REST_API_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("KV_REST_API_TOKEN")
        return cls(url, token) if url and token else None

    async def _pipeline(self, commands: list[list[str]]) -> list:
        async with httpx.AsyncClient(timeout=6.0) as c:
            r = await c.post(f"{self.url}/pipeline", json=commands, headers={"Authorization": f"Bearer {self.token}"})
            r.raise_for_status()
            return r.json()

    async def get_levels(self, zone_ids: list[str]) -> dict[str, str]:
        res = await self._pipeline([["GET", f"porto:level:{i}"] for i in zone_ids])
        return {i: r["result"] for i, r in zip(zone_ids, res) if r.get("result") in ORDER}

    async def set_level(self, zone_id: str, level: str) -> None:
        await self._pipeline([["SET", f"porto:level:{zone_id}", level]])


class NtfySender:
    def __init__(self, prefix: str, base_url: str = "https://ntfy.sh") -> None:
        self.prefix, self.base_url = prefix, base_url.rstrip("/")

    @classmethod
    def from_env(cls) -> "NtfySender | None":
        prefix = os.environ.get("NTFY_TOPIC_PREFIX")
        return cls(prefix, os.environ.get("NTFY_URL", "https://ntfy.sh")) if prefix else None

    async def send(self, n: Notification) -> None:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.post(
                self.base_url,
                json={"topic": f"{self.prefix}-{n.zone_id}", "title": n.title, "message": n.message,
                      "priority": n.priority, "tags": n.tags},
            )
            r.raise_for_status()
