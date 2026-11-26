"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { HAZARD_LABEL, LEVEL_COLOR, LEVEL_LABEL, type AlertsResponse } from "./types";

// Leaflet precisa do `window`: carregar só no cliente
const AlertMap = dynamic(() => import("./Map"), {
  ssr: false,
  loading: () => <div className="map-loading">A carregar mapa…</div>,
});

export default function Home() {
  const [data, setData] = useState<AlertsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    // ?demo=chuva|calor|tempestade mostra uma SIMULAÇÃO (para testar o painel)
    const demo = new URLSearchParams(window.location.search).get("demo");
    const url = demo ? `/api/alerts?demo=${encodeURIComponent(demo)}` : "/api/alerts";
    const load = () =>
      fetch(url)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
        .then((d: AlertsResponse) => {
          setData(d);
          setError(null);
        })
        .catch((e: Error) => setError(e.message));
    load();
    const id = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <main>
      <header>
        <h1>Porto Resiliente</h1>
        <p>Cheias, calor, vento e qualidade do ar, por zona da cidade.</p>
      </header>

      {data?.simulated && (
        <div className="sim-banner" role="alert">
          SIMULAÇÃO: estes alertas são fictícios e não refletem a situação real no Porto.
        </div>
      )}

      <div className="layout">
        <section className="panel" aria-label="Alertas por zona">
          {error && <p className="error">Não foi possível carregar os alertas ({error}).</p>}
          {!data && !error && <p>A carregar…</p>}
          {data?.zones.map((z) => (
            <article
              key={z.id}
              className={`zone ${selected === z.id ? "selected" : ""}`}
              onClick={() => setSelected(z.id)}
            >
              <div className="zone-head">
                <span className="dot" style={{ background: LEVEL_COLOR[z.level] }} />
                <h2>{z.name}</h2>
                <span className="level">{LEVEL_LABEL[z.level]}</span>
              </div>
              {z.hazards.length === 0 ? (
                <p className="muted">Sem alertas ativos.</p>
              ) : (
                <ul>
                  {z.hazards.map((h, i) => (
                    <li key={i}>
                      <span className="dot small" style={{ background: LEVEL_COLOR[h.level] }} />
                      <strong>{HAZARD_LABEL[h.type] ?? h.type}</strong>: {h.reason}
                      <div className="muted">Fonte: {h.source}</div>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          ))}
          {data && (
            <footer className="muted">
              <p>Atualizado: {new Date(data.updated_at).toLocaleString("pt-PT")}</p>
              <p>Fontes: {data.sources.join("; ")}</p>
              {data.notes.map((n, i) => (
                <p key={i}>{n}</p>
              ))}
            </footer>
          )}
        </section>

        <section className="map" aria-label="Mapa do Porto">
          {data && <AlertMap zones={data.zones} selected={selected} onSelect={setSelected} />}
        </section>
      </div>
    </main>
  );
}
