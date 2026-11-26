export type LevelName = "green" | "yellow" | "orange" | "red";

export interface Hazard {
  type: string;
  level: LevelName;
  reason: string;
  source: string;
  valid_from?: string | null; // hora de Lisboa, sem fuso
  valid_until?: string | null;
}

export interface DayForecast {
  date: string | null;
  precip_prob: number | null;
  precip_class: number | null;
  t_min: number | null;
  t_max: number | null;
  wind_class: number | null;
}

export interface AirQuality {
  eaqi: number;
  label: string;
  modeled: boolean;
}

export interface ZoneAlert {
  id: string;
  name: string;
  lat: number;
  lon: number;
  level: LevelName;
  hazards: Hazard[];
}

export interface AlertsResponse {
  simulated?: boolean;
  updated_at: string;
  sources: string[];
  notes: string[];
  forecast?: DayForecast | null;
  air_quality?: AirQuality | null;
  zones: ZoneAlert[];
}

export const PRECIP_CLASS: Record<number, string> = { 1: "fraca", 2: "moderada", 3: "forte" };
export const WIND_CLASS: Record<number, string> = { 1: "fraco", 2: "moderado", 3: "forte", 4: "muito forte" };

// Formatação por texto (sem `Date`): evita deslocar datas por fuso horário do visitante.
// "2026-11-27T12:00:00" -> "27/11 12:00"; "2026-11-26" -> "26/11"
export function fmtDateTime(iso?: string | null): string | null {
  const m = iso?.match(/^\d{4}-(\d{2})-(\d{2})(?:T(\d{2}:\d{2}))?/);
  return m ? `${m[2]}/${m[1]}${m[3] ? ` ${m[3]}` : ""}` : null;
}

export const LEVEL_COLOR: Record<LevelName, string> = {
  green: "#2e9e5b",
  yellow: "#e6b800",
  orange: "#ef8a17",
  red: "#d33a3a",
};

export const LEVEL_LABEL: Record<LevelName, string> = {
  green: "Sem alertas",
  yellow: "Atenção",
  orange: "Risco elevado",
  red: "Risco muito elevado",
};

export const HAZARD_LABEL: Record<string, string> = {
  cheias: "Cheias",
  chuva: "Chuva",
  calor: "Calor",
  frio: "Frio",
  vento: "Vento",
  trovoada: "Trovoada",
  nevoeiro: "Nevoeiro",
  agitacao_maritima: "Agitação marítima",
  qualidade_ar: "Qualidade do ar",
  neve: "Neve",
};
