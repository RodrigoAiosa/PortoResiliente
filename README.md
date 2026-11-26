# Porto Resiliente

Alertas de **cheias, calor, vento e qualidade do ar** por zona do Porto.
Backend em **Python (FastAPI)**, front-end em **Next.js + Leaflet**, deploy na **Vercel**.

## Fontes de dados

| Fonte | Uso | Estado |
|---|---|---|
| IPMA, avisos (`warnings_www.json`, área `PTO`) | Avisos oficiais ativos | Oficial, verificada |
| IPMA, previsão diária (`globalIdLocal` 1131200) | Chuva, temperatura | Oficial, verificada |
| Open-Meteo / CAMS | Índice europeu de qualidade do ar | **Modelado** (não são medições), opcional; respondeu em produção em 2026-11-26 |
| QualAr/APA, SNIRH (rios) | Medições reais | **Não integradas**: sem API pública estável confirmada |

Os limiares de cheias e calor em `porto_resiliente/rules.py` são **heurísticas locais**
e devem ser validados/ajustados com a Proteção Civil e dados históricos. Esta app é
informativa e não substitui os avisos oficiais. Em emergência, ligue 112.

## Estrutura

```
api/index.py            FastAPI (função Python da Vercel): /api/alerts, /api/health
porto_resiliente/       ipma.py, airquality.py, rules.py (puro/testável), zones.py, service.py
tests/                  pytest (regras + API sem rede)
app/                    Next.js (painel + mapa)
```

## Desenvolvimento

```bash
pip install -r requirements-dev.txt && pytest      # backend
npm install && npm run build                        # front-end
vercel dev                                          # Next.js + API Python juntos
# ou: uvicorn api.index:app --port 8000  e  API_PROXY=http://localhost:8000 npm run dev
```

## Deploy

Importe o repositório na Vercel (preset Next.js). `/api/*` é reescrito para `api/index.py`.
A resposta é cacheada na CDN (`s-maxage=300`), por isso não precisa de base de dados no MVP.

## Roadmap

1. Integrar medições reais da QualAr e níveis do Douro (SNIRH) quando houver acesso estável
2. Denúncias de cidadãos (foto → classificação por IA → fluxo de estados) com Vercel Blob + Workflow
3. Notificações (e-mail/push) por zona usando Vercel Cron + Queues
4. Calibrar limiares com histórico de ocorrências
