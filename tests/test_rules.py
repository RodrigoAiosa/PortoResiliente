from datetime import datetime

from porto_resiliente.ipma import parse_forecast, parse_warnings
from porto_resiliente.models import Level
from porto_resiliente.rules import air_level, evaluate_zone, flood_level, heat_level
from porto_resiliente.zones import ZONES

RIBEIRA = next(z for z in ZONES if z.id == "ribeira")
BOAVISTA = next(z for z in ZONES if z.id == "boavista")
FOZ = next(z for z in ZONES if z.id == "foz")
NOW = datetime(2026, 11, 26, 15, 0)

RAW_WARNINGS = [
    {"idAreaAviso": "PTO", "awarenessTypeName": "Precipitação", "awarenessLevelID": "orange",
     "startTime": "2026-11-26T12:00:00", "endTime": "2026-11-27T12:00:00", "text": ""},
    {"idAreaAviso": "PTO", "awarenessTypeName": "Nevoeiro", "awarenessLevelID": "green",
     "startTime": "2026-11-26T12:00:00", "endTime": "2026-11-27T12:00:00", "text": ""},
    {"idAreaAviso": "LSB", "awarenessTypeName": "Vento", "awarenessLevelID": "red",
     "startTime": "2026-11-26T12:00:00", "endTime": "2026-11-27T12:00:00", "text": ""},
    {"idAreaAviso": "PTO", "awarenessTypeName": "Agitação Marítima", "awarenessLevelID": "yellow",
     "startTime": "2026-11-26T12:00:00", "endTime": "2026-11-27T12:00:00", "text": ""},
    {"idAreaAviso": "PTO", "awarenessTypeName": "Vento", "awarenessLevelID": "yellow",
     "startTime": "2026-11-20T12:00:00", "endTime": "2026-11-21T12:00:00", "text": ""},  # expirado
]

RAW_FORECAST = {
    "data": [
        {"forecastDate": "2026-11-26", "precipitaProb": "76.0", "tMin": "8.1", "tMax": "14.6",
         "classWindSpeed": 1, "classPrecInt": 2},
        {"forecastDate": "2026-11-27", "precipitaProb": "10.0", "tMin": "9", "tMax": "15",
         "classWindSpeed": 1},
    ]
}


def test_parse_warnings_filters_area_level_and_time():
    out = parse_warnings(RAW_WARNINGS, NOW)
    names = {w["type_name"] for w in out}
    assert names == {"Precipitação", "Agitação Marítima"}


def test_parse_forecast_converts_numbers_and_missing_fields():
    f = parse_forecast(RAW_FORECAST)
    assert f[0]["precip_prob"] == 76.0 and f[0]["precip_class"] == 2
    assert f[1]["precip_class"] is None


def test_flood_from_forecast_only():
    lvl, reason = flood_level(parse_forecast(RAW_FORECAST), Level.GREEN)
    assert lvl == Level.YELLOW and "26/11" in reason and "2026" not in reason


def test_official_warning_raises_flood_level():
    lvl, _ = flood_level([], Level.ORANGE)
    assert lvl == Level.ORANGE


def test_heat_thresholds():
    assert heat_level([{"date": "d", "t_max": 31.9}])[0] == Level.GREEN
    assert heat_level([{"date": "d", "t_max": 35.0}])[0] == Level.ORANGE
    assert heat_level([{"date": "d", "t_max": 40.0}])[0] == Level.RED


def test_air_level():
    assert air_level(None)[0] == Level.GREEN
    assert air_level(45)[0] == Level.GREEN
    assert air_level(85)[0] == Level.ORANGE


def test_ribeira_reports_flood_not_generic_rain():
    z = evaluate_zone(RIBEIRA, parse_warnings(RAW_WARNINGS, NOW), parse_forecast(RAW_FORECAST), None)
    types = {h.type for h in z.hazards}
    assert "cheias" in types and "chuva" not in types
    assert z.level == "orange"
    assert "agitacao_maritima" not in types  # Ribeira não é costeira


def test_non_flood_zone_gets_generic_rain():
    z = evaluate_zone(BOAVISTA, parse_warnings(RAW_WARNINGS, NOW), parse_forecast(RAW_FORECAST), None)
    assert {h.type for h in z.hazards} == {"chuva"}


def test_coastal_zone_gets_sea_agitation():
    z = evaluate_zone(FOZ, parse_warnings(RAW_WARNINGS, NOW), [], None)
    assert "agitacao_maritima" in {h.type for h in z.hazards}


def test_all_green():
    z = evaluate_zone(BOAVISTA, [], [], None)
    assert z.level == "green" and z.hazards == []


def test_reasons_use_portuguese_level_names():
    lvl, reason = flood_level([], Level.RED)
    assert "vermelho" in reason and "red" not in reason
    z = evaluate_zone(BOAVISTA, parse_warnings(RAW_WARNINGS, NOW), [], None)
    assert "laranja" in z.hazards[0].reason


def test_air_label_bands():
    from porto_resiliente.rules import air_label

    assert [air_label(x) for x in (10, 20, 59, 60, 85, 100, 150)] == [
        "Boa", "Razoável", "Moderada", "Fraca", "Muito fraca", "Extremamente fraca", "Extremamente fraca"]


def test_flood_window_only_when_official_warning_sets_level():
    ws = parse_warnings(RAW_WARNINGS, NOW)  # aviso laranja de precipitação
    z = evaluate_zone(RIBEIRA, ws, parse_forecast(RAW_FORECAST), None)
    cheias = next(h for h in z.hazards if h.type == "cheias")
    assert cheias.valid_from == "2026-11-26T12:00:00" and cheias.valid_until == "2026-11-27T12:00:00"
    # só previsão (sem aviso): sem janela
    z2 = evaluate_zone(RIBEIRA, [], parse_forecast(RAW_FORECAST), None)
    c2 = next(h for h in z2.hazards if h.type == "cheias")
    assert c2.valid_from is None and c2.valid_until is None


def test_dm_formats_and_tolerates_bad_input():
    from porto_resiliente.rules import _dm

    assert _dm("2026-11-26") == "26/11" and _dm(None) == "data desconhecida" and _dm("xx") == "xx"
    assert "26/11" in heat_level([{"date": "2026-11-26", "t_max": 36.0}])[1]
