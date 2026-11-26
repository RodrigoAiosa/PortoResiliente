import hmac
import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Response

from porto_resiliente import notify
from porto_resiliente.models import AlertsResponse
from porto_resiliente.service import build_alerts

app = FastAPI(title="Porto Resiliente API", version="0.2.0")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/alerts", response_model=AlertsResponse)
async def alerts(
    response: Response,
    demo: Literal["chuva", "calor", "tempestade"] | None = None,
    refresh: bool = False,
) -> AlertsResponse:
    """Alertas por zona.

    `?demo=chuva|calor|tempestade` devolve uma SIMULAÇÃO (simulated=true).
    `?refresh=1` ignora a cache da CDN (o servidor ainda limita a ~1 consulta/min ao IPMA).
    """
    if demo or refresh:
        response.headers["Cache-Control"] = "no-store"
    else:
        # cache na CDN da Vercel: 5 min, serve versão antiga enquanto revalida
        response.headers["Cache-Control"] = "public, s-maxage=300, stale-while-revalidate=600"
    return await build_alerts(demo)


@app.get("/api/cron/notify")
async def cron_notify(authorization: str | None = Header(default=None)) -> dict:
    """Chamado pela Vercel Schedules. Recusa pedidos sem CRON_SECRET (falha fechada)."""
    secret = os.environ.get("CRON_SECRET", "")
    if len(secret) < 16 or not hmac.compare_digest(authorization or "", f"Bearer {secret}"):
        raise HTTPException(status_code=401, detail="unauthorized")
    min_level = os.environ.get("NOTIFY_MIN_LEVEL", "orange")
    if min_level not in notify.ORDER or min_level == "green":
        min_level = "orange"
    alerts = await build_alerts(use_cache=False)  # o cron decide sempre com dados frescos
    return await notify.run(alerts, notify.UpstashStore.from_env(), notify.NtfySender.from_env(), min_level)
