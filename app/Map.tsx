"use client";

import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import {
  HAZARD_LABEL,
  LEVEL_COLOR,
  LEVEL_LABEL,
  PRECIP_CLASS,
  WIND_CLASS,
  fmtDateTime,
  type AirQuality,
  type DayForecast,
  type Hazard,
  type ZoneAlert,
} from "./types";

function validity(h: Hazard): string | null {
  const from = fmtDateTime(h.valid_from);
  const until = fmtDateTime(h.valid_until);
  if (from && until) return `Válido de ${from} a ${until} (hora de Lisboa)`;
  return until ? `Válido até ${until} (hora de Lisboa)` : null;
}

function ForecastLine({ f }: { f: DayForecast }) {
  const parts: string[] = [];
  if (f.precip_prob != null) {
    const cls = f.precip_class != null ? PRECIP_CLASS[f.precip_class] : undefined;
    parts.push(`chuva ${Math.round(f.precip_prob)}%${cls ? ` (${cls})` : ""}`);
  }
  if (f.t_min != null && f.t_max != null) parts.push(`${Math.round(f.t_min)}–${Math.round(f.t_max)} °C`);
  if (f.wind_class != null) parts.push(`vento ${WIND_CLASS[f.wind_class] ?? `classe ${f.wind_class}`}`);
  if (parts.length === 0) return null;
  return (
    <div className="pop-line">
      <strong>Previsão{fmtDateTime(f.date) ? ` ${fmtDateTime(f.date)}` : ""}:</strong> {parts.join(" · ")}
    </div>
  );
}

export default function AlertMap({
  zones,
  forecast,
  air,
  selected,
  onSelect,
}: {
  zones: ZoneAlert[];
  forecast?: DayForecast | null;
  air?: AirQuality | null;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <MapContainer center={[41.153, -8.62]} zoom={12} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {zones.map((z) => (
        <CircleMarker
          key={z.id}
          center={[z.lat, z.lon]}
          radius={selected === z.id ? 20 : 15}
          pathOptions={{
            color: "#fff",
            weight: 2,
            fillColor: LEVEL_COLOR[z.level],
            fillOpacity: 0.85,
          }}
          eventHandlers={{ click: () => onSelect(z.id) }}
        >
          {/* Resumo ao passar o rato (não existe em ecrãs táteis: o detalhe está no popup) */}
          <Tooltip direction="top" offset={[0, -10]}>
            <strong>{z.name}</strong>: {LEVEL_LABEL[z.level]}
            {z.hazards.length > 0 && ` · ${z.hazards.length} risco${z.hazards.length > 1 ? "s" : ""}`}
          </Tooltip>

          <Popup minWidth={240} maxWidth={320}>
            <div className="popup">
              <div className="pop-head">
                <span className="pop-dot" style={{ background: LEVEL_COLOR[z.level] }} />
                <strong>{z.name}</strong>
                <span className="pop-level">{LEVEL_LABEL[z.level]}</span>
              </div>

              {z.hazards.length === 0 ? (
                <p className="pop-muted">Sem alertas ativos.</p>
              ) : (
                <ul className="pop-list">
                  {z.hazards.map((h, i) => (
                    <li key={i}>
                      <span className="pop-dot small" style={{ background: LEVEL_COLOR[h.level] }} />
                      <strong>{HAZARD_LABEL[h.type] ?? h.type}</strong>: {h.reason}
                      <div className="pop-muted">
                        Fonte: {h.source}
                        {validity(h) && <> · {validity(h)}</>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              {(forecast || air) && <hr />}
              {forecast && <ForecastLine f={forecast} />}
              {air && (
                <div className="pop-line">
                  <strong>Qualidade do ar:</strong> {air.label} (índice {Math.round(air.eaqi)}
                  {air.modeled ? ", modelado" : ""})
                </div>
              )}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
