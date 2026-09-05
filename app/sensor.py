"""
Ingesta de lecturas del sensor ultrasónico real (ESP32 + HC-SR04).

Firmware real (ver proyecto_copy_....ino): el ESP32 mide distancia
con un sensor ultrasónico sobre una MAQUETA a escala (altura de la
maqueta: 0.15 m) y la escala matemáticamente a metros "reales"
(altura real simulada: 15 m):

    nivelMaqueta = ALTURA_MAQUETA - distancia_medida   (0 a 0.15 m)
    nivelReal    = nivelMaqueta * ALTURA_REAL / ALTURA_MAQUETA   (0 a 15 m)

El ESP32 ya hace esta conversión a bordo y expone el resultado
(nivel en metros "reales") en su propio endpoint HTTP GET /nivel.
Este backend NO recibe una distancia cruda: recibe el nivel ya
calculado por el firmware.

Conectividad real:
    Sensor ultrasónico (HC-SR04) -> ESP32 -> WiFi -> este backend

El ESP32 se conecta a un WiFi (actualmente el hotspot de un celular,
red privada) y por defecto solo SIRVE datos en su propia IP local
(GET /nivel) — no los envía a nadie. Como este backend corre en
internet (fuera de esa red privada), no puede ir a buscar esa IP
local directamente. Por eso el firmware se extendió (ver .ino
actualizado) para que además haga un POST periódico hacia este
backend con su lectura — así el ESP32 empuja el dato en vez de
esperar que alguien se lo pida.
"""

from datetime import datetime, timedelta

# Buffer en memoria de la última lectura real recibida por estación, y de
# el historial de lecturas reales de los últimos 7 días (para /api/history).
# En producción esto se persistiría en base de datos (tabla de series de
# tiempo) — ver nota de persistencia en README — pero para la demo alcanza
# con guardar en memoria mientras el proceso está vivo.
_last_readings: dict[str, dict] = {}
_history: dict[str, list[dict]] = {}

# Cuánto guardamos de historial real antes de empezar a descartar lo viejo.
_HISTORY_RETENTION = timedelta(days=7)


def record_sensor_reading(station_id: str, level_m: float) -> dict:
    """Registra una lectura real ya calculada por el firmware del ESP32.

    level_m es el nivel en metros "reales" que el propio ESP32 calcula
    (ver handleNivel() en el .ino) — este backend no vuelve a convertir
    nada, solo guarda y expone el dato.
    """
    now = datetime.utcnow()
    reading = {
        "station_id": station_id,
        "level_m": round(level_m, 3),
        "timestamp": now.isoformat() + "Z",
        "source": "sensor",
    }
    _last_readings[station_id] = reading

    points = _history.setdefault(station_id, [])
    points.append({"timestamp": reading["timestamp"], "level_m": reading["level_m"]})
    cutoff = now - _HISTORY_RETENTION
    _history[station_id] = [p for p in points if datetime.fromisoformat(p["timestamp"].rstrip("Z")) >= cutoff]

    return reading


def get_last_sensor_reading(station_id: str) -> dict | None:
    return _last_readings.get(station_id)


def has_real_data(station_id: str) -> bool:
    return station_id in _last_readings


def get_real_history(station_id: str, hours: int) -> list[dict] | None:
    """Puntos reales de las últimas `hours` horas para una estación, o None
    si todavía no hay ninguna lectura real (para que el caller decida si
    cae al historial simulado)."""
    points = _history.get(station_id)
    if not points:
        return None
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    filtered = [p for p in points if datetime.fromisoformat(p["timestamp"].rstrip("Z")) >= cutoff]
    return filtered if filtered else points[-1:]
