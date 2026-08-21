"""
Ingesta de lecturas del sensor ultrasónico real (ESP32 + HC-SR04).

Firmware real (ver proyecto_copy_....ino): el ESP32 mide distancia
con un sensor ultrasónico sobre una MAQUETA a escala (altura de la
maqueta: 0.25 m) y la escala matemáticamente a metros "reales"
(altura real simulada: 12 m):

    nivelMaqueta = ALTURA_MAQUETA - distancia_medida   (0 a 0.25 m)
    nivelReal    = nivelMaqueta * ALTURA_REAL / ALTURA_MAQUETA   (0 a 12 m)

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

from datetime import datetime

# Buffer en memoria de la última lectura real recibida por estación.
# En producción esto se persistiría en base de datos (tabla de series
# de tiempo), pero para la demo alcanza con guardar la última lectura.
_last_readings: dict[str, dict] = {}


def record_sensor_reading(station_id: str, level_m: float) -> dict:
    """Registra una lectura real ya calculada por el firmware del ESP32.

    level_m es el nivel en metros "reales" que el propio ESP32 calcula
    (ver handleNivel() en el .ino) — este backend no vuelve a convertir
    nada, solo guarda y expone el dato.
    """
    reading = {
        "station_id": station_id,
        "level_m": round(level_m, 3),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "sensor",
    }
    _last_readings[station_id] = reading
    return reading


def get_last_sensor_reading(station_id: str) -> dict | None:
    return _last_readings.get(station_id)


def has_real_data(station_id: str) -> bool:
    return station_id in _last_readings
