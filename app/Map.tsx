"use client";

import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { HAZARD_LABEL, LEVEL_COLOR, LEVEL_LABEL, type ZoneAlert } from "./types";

export default function Map({
  zones,
  selected,
  onSelect,
}: {
  zones: ZoneAlert[];
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
          <Popup>
            <strong>{z.name}</strong>
            <br />
            {LEVEL_LABEL[z.level]}
            {z.hazards.map((h, i) => (
              <div key={i}>• {HAZARD_LABEL[h.type] ?? h.type}</div>
            ))}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
