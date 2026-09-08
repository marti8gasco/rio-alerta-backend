"""
Simulador de lecturas de NIVEL de río (metros), no caudal.

En producción, este modulo se reemplaza por datos reales del sensor
(ver sensor.py para la conversión distancia -> nivel). La forma de
los datos que devuelve (get_current_reading, get_history) es el
contrato que el resto de la API espera, asi que conectar el sensor
real es cuestion de reimplementar estas funciones sin tocar los
endpoints — o directamente usar record_sensor_reading de sensor.py
para las estaciones que ya tengan datos reales.
"""

import random
from datetime import datetime, timedelta

STATIONS = {
    "km18": {"name": "Km 18", "base_level": 1.8, "lat": -34.55, "lon": -56.35},
    "km42": {"name": "Km 95", "base_level": 3.0, "lat": -34.62, "lon": -56.28},
    "km65": {"name": "Km 65", "base_level": 1.2, "lat": -34.70, "lon": -56.15},
}

# Estado en memoria para el random walk (se reinicia si se reinicia el server)
_state = {station_id: float(info["base_level"]) for station_id, info in STATIONS.items()}


def _step_level(station_id: str) -> float:
    """Avanza el nivel simulado con un random walk acotado, no ruido puro."""
    current = _state[station_id]
    delta = random.uniform(-0.08, 0.1)  # sesgo levemente positivo para poder demostrar alertas
    new_value = max(0.0, current + delta)
    _state[station_id] = new_value
    return round(new_value, 2)


def get_current_reading(station_id: str) -> dict:
    if station_id not in STATIONS:
        raise ValueError(f"Estacion desconocida: {station_id}")
    level = _step_level(station_id)
    return {
        "station_id": station_id,
        "station_name": STATIONS[station_id]["name"],
        "level_m": level,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "simulated",
    }


def get_all_current_readings() -> list[dict]:
    return [get_current_reading(sid) for sid in STATIONS]


def get_history(station_id: str, hours: int = 24) -> list[dict]:
    """Genera una serie historica simulada, coherente con el valor base de la estacion."""
    if station_id not in STATIONS:
        raise ValueError(f"Estacion desconocida: {station_id}")
    base = STATIONS[station_id]["base_level"]
    points = []
    now = datetime.utcnow()
    value = base * 0.7
    step_minutes = max(1, (hours * 60) // 48)  # ~48 puntos en la serie
    total_steps = (hours * 60) // step_minutes

    for i in range(total_steps, -1, -1):
        ts = now - timedelta(minutes=i * step_minutes)
        value = max(0.0, value + random.uniform(-0.05, 0.08))
        points.append({
            "timestamp": ts.isoformat() + "Z",
            "level_m": round(value, 2),
        })
    return points


def get_stations_summary() -> list[dict]:
    result = []
    for sid, info in STATIONS.items():
        reading = get_current_reading(sid)
        result.append({
            "station_id": sid,
            "name": info["name"],
            "lat": info["lat"],
            "lon": info["lon"],
            "level_m": reading["level_m"],
        })
    return result
