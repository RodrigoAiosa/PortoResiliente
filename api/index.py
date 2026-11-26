from fastapi import FastAPI, Response

from porto_resiliente.models import AlertsResponse
from porto_resiliente.service import build_alerts

app = FastAPI(title="Porto Resiliente API", version="0.1.0")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/alerts", response_model=AlertsResponse)
async def alerts(response: Response) -> AlertsResponse:
    # cache na CDN da Vercel: 5 min, serve versão antiga enquanto revalida
    response.headers["Cache-Control"] = "public, s-maxage=300, stale-while-revalidate=600"
    return await build_alerts()
