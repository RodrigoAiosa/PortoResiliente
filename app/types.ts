export type LevelName = "green" | "yellow" | "orange" | "red";

export interface Hazard {
  type: string;
  level: LevelName;
  reason: string;
  source: string;
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
  zones: ZoneAlert[];
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
