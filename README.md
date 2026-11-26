# Porto Resiliente

Alertas de **cheias, calor, vento e qualidade do ar** por zona do Porto.
Backend em **Python (FastAPI)**, front-end em **Next.js + Leaflet**, deploy na **Vercel**.

> Informação indicativa. Não substitui os avisos oficiais da Proteção Civil e do IPMA.
> Em emergência, ligue **112**.

## Fontes de dados

| Fonte | Uso | Estado |
|---|---|---|
| IPMA, avisos (`warnings_www.json`, área `PTO`) | Avisos oficiais ativos | Oficial, verificada |
| IPMA, previsão diária (`globalIdLocal` 1131200) | Chuva, temperatura | Oficial, verificada |
| Open-Meteo / CAMS | Índice europeu de qualidade do ar | **Modelado** (não são medições); respondeu em produção em 2026-11-26 |
| SNIRH/APA (níveis de rios) | Cheias | **Não integrada** (ver abaixo) |
| QualAr/APA (medições do ar) | Qualidade do ar | **Não integrada** (ver abaixo) |

### Por que SNIRH e QualAr não estão integrados (pesquisa de 2026-11-26)

- **SNIRH (Portugal):** não encontrei uma API pública estável com níveis em tempo real.
  O conjunto «Informação Hidrológica do Rio Douro» (limnímetros da APDL, licença ODC Attribution)
  no dados.gov.pt não tem ficheiros nem API disponíveis e está marcado como atualização pontual
  (última em 2024-05-29).
- **QualAr:** o portal da APA permite consulta e descarga de dados históricos validados, mas não
  encontrei uma API pública documentada para tempo real. O agregador aqicn.org redistribui estes
  dados mas exige chave e tem termos de uso próprios.

Se a APA ou a APDL disponibilizarem uma API, o ponto de entrada é `porto_resiliente/airquality.py`
(ar) e um novo módulo para rios, ligado em `rules.flood_level`.

Os limiares de cheias e calor em `porto_resiliente/rules.py` são **heurísticas locais** e devem
ser validados com a Proteção Civil. Aviso e previsão vêm do mesmo IPMA, por isso a regra usa o
nível mais alto e não os soma.

## Estrutura

```
api/index.py            FastAPI (função Python da Vercel): /api/alerts, /api/health, /api/cron/notify
porto_resiliente/       ipma, airquality, rules (puro), zones, service, demo, notify
tests/                  pytest (regras, API, notificações; tudo sem rede)
app/                    Next.js (painel + mapa)
```

## Simulação (testar sem mau tempo)

`/api/alerts?demo=chuva|calor|tempestade` devolve alertas **fictícios** com `simulated: true`
(sem cache). O painel mostra um aviso vermelho de simulação:

- `https://portoresiliente.vercel.app/?demo=chuva`
- `https://portoresiliente.vercel.app/?demo=tempestade`

As simulações nunca disparam notificações.

## Notificações por zona (push via ntfy)

Uma agenda da Vercel (a cada 15 min) chama `/api/cron/notify`, que compara o nível atual de cada
zona com o último guardado e envia push só quando o nível **sobe até ao mínimo** (por omissão
`orange`) ou quando a zona **normaliza**. Não envia nada se o IPMA estiver indisponível.

Cada zona tem o seu tópico: `{NTFY_TOPIC_PREFIX}-{zona}` (`ribeira`, `foz`, `campanha`, `boavista`,
`paranhos`). Quem quiser receber avisos subscreve o tópico da sua zona na app ntfy.

Variáveis de ambiente (Vercel → Settings → Environment Variables):

| Variável | Obrigatória | Descrição |
|---|---|---|
| `CRON_SECRET` | sim | ≥ 16 caracteres aleatórios. A Vercel envia-o como `Bearer` à agenda. Sem ele a rota responde 401. |
| `NTFY_TOPIC_PREFIX` | sim | Prefixo **longo e imprevisível**: os tópicos do ntfy.sh são públicos. |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | sim | Guarda o último nível por zona (Upstash Redis pelo Marketplace da Vercel; `KV_REST_API_*` também é aceite). |
| `NOTIFY_MIN_LEVEL` | não | `yellow`, `orange` (padrão) ou `red`. |
| `NTFY_URL` | não | Servidor ntfy próprio (padrão `https://ntfy.sh`). |

Sem Redis ou sem `NTFY_TOPIC_PREFIX` a rota corre em **modo de ensaio** (calcula, não envia).
Se um envio falhar, o estado dessa zona não é atualizado e tenta-se de novo na execução seguinte.

## Desenvolvimento

```bash
pip install -r requirements-dev.txt && pytest      # backend
npm install && npm run build                        # front-end
vercel dev                                          # Next.js + API Python juntos
# ou: uvicorn api.index:app --port 8000  e  API_PROXY=http://localhost:8000 npm run dev
```

## Deploy

Importe o repositório na Vercel (preset Next.js). `/api/*` é reescrito para `api/index.py`.
`/api/alerts` é cacheado na CDN (`s-maxage=300`).

## Roadmap

1. Medições reais da QualAr e níveis do Douro, se surgir acesso estável
2. Calibrar limiares com histórico de ocorrências
3. Subscrição por e-mail (hoje só push via ntfy)
