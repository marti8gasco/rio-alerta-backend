"""
RioAlerta API — backend de demo para monitoreo de NIVEL de río.

Métrica: nivel del río en metros (no caudal). Se descartó medir
caudal: el sensor no lo mide directamente y no es proporcional al
nivel (depende de la geometría del cauce y otros factores). El nivel
es la métrica que se usa en la práctica (ver boletines del CECOED
San José).

Hardware real: sensor ultrasónico HC-SR04 + ESP32 (no "CPL32" — fue
una confusión de nombre; el firmware real usa un ESP32). El ESP32
mide sobre una maqueta a escala y escala el resultado a metros
"reales" a bordo (ver app/sensor.py para el detalle). El ESP32 se
conecta a un WiFi y por defecto solo sirve datos en su propia IP
local (GET /nivel) — no empuja nada. Como este backend corre en
internet, separado de esa red local, el firmware se extendió para
que además haga POST periódico hacia /api/sensor/reading con su
lectura.

Datos simulados por defecto: los valores de nivel para estaciones sin
lectura real son generados por un random walk (ver simulator.py).
Cuando una estación recibe al menos una lectura real via
POST /api/sensor/reading, esa estación empieza a devolver el dato
real en vez del simulado (ver current_reading).

Correr localmente:
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Documentacion interactiva en http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import simulator, thresholds, notifications, sensor

app = FastAPI(
    title="RioAlerta API",
    description="API de demo para monitoreo de nivel de río y alertas de evacuación.",
    version="0.2.0",
)

# CORS abierto para la demo. En produccion, restringir a los origenes
# reales del frontend (dominio de la app web / app movil empaquetada).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas de request
# ---------------------------------------------------------------------------

class ThresholdsUpdate(BaseModel):
    atencion: float = Field(..., gt=0, description="Umbral de atencion, nivel en metros")
    evacuacion: float = Field(..., gt=0, description="Umbral de evacuacion, nivel en metros")


class NotificationCreate(BaseModel):
    type: str = Field(..., pattern="^(info|warning|success)$")
    text: str = Field(..., min_length=1, max_length=280)


class SensorReadingCreate(BaseModel):
    station_id: str = Field(..., description="Id de la estacion, ej. 'km42'")
    nivel: float = Field(
        ..., ge=0, le=12,
        description="Nivel en metros ya calculado por el firmware del ESP32 (0 a 12)",
    )
    alerta: str | None = Field(
        None, description="Alerta calculada por el firmware (informativa; el backend recalcula la propia)"
    )


# ---------------------------------------------------------------------------
# Salud del servicio
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Ingesta del sensor real
# ---------------------------------------------------------------------------

@app.post("/api/sensor/reading", status_code=201)
def receive_sensor_reading(payload: SensorReadingCreate):
    """
    Punto de entrada para la lectura del sensor real (ESP32).

    El ESP32 ya calcula el nivel en metros a bordo (ver handleNivel()
    en el firmware) y lo manda tal cual — este backend no vuelve a
    convertir nada, solo guarda la lectura y recalcula el status con
    los umbrales configurados acá (por si difieren de los que tiene
    el firmware hardcodeados).

    Payload que manda el ESP32 (mismo JSON que ya devuelve su propio
    endpoint GET /nivel, más el station_id):
        { "station_id": "km42", "nivel": 3.30, "alerta": "Normal" }
    """
    reading = sensor.record_sensor_reading(payload.station_id, payload.nivel)
    reading["status"] = thresholds.status_from_level(reading["level_m"])
    return reading


@app.get("/api/sensor/reading")
def last_sensor_reading(station_id: str = "km42"):
    """Última lectura real recibida del sensor para una estación (o 404 si no hay ninguna aún)."""
    reading = sensor.get_last_sensor_reading(station_id)
    if reading is None:
        raise HTTPException(status_code=404, detail=f"Sin lecturas reales para {station_id} todavía")
    reading = dict(reading)
    reading["status"] = thresholds.status_from_level(reading["level_m"])
    return reading


# ---------------------------------------------------------------------------
# Dashboard / lectura actual
# ---------------------------------------------------------------------------

@app.get("/api/reading/current")
def current_reading(station_id: str = "km42"):
    """
    Lectura actual de una estacion, con el status de alerta ya calculado.
    Si la estación tiene al menos una lectura real del sensor, se
    devuelve esa; si no, se devuelve una lectura simulada.
    """
    if sensor.has_real_data(station_id):
        reading = dict(sensor.get_last_sensor_reading(station_id))
    else:
        try:
            reading = simulator.get_current_reading(station_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    reading["status"] = thresholds.status_from_level(reading["level_m"])
    return reading


@app.get("/api/reading/all")
def all_readings():
    """Lectura actual de todas las estaciones, para el mapa."""
    readings = simulator.get_all_current_readings()
    for r in readings:
        if sensor.has_real_data(r["station_id"]):
            real = sensor.get_last_sensor_reading(r["station_id"])
            r["level_m"] = real["level_m"]
            r["source"] = "sensor"
        r["status"] = thresholds.status_from_level(r["level_m"])
    return readings


# ---------------------------------------------------------------------------
# Historico
# ---------------------------------------------------------------------------

@app.get("/api/history")
def history(station_id: str = "km42", hours: int = 24):
    """
    Serie historica de nivel (m). hours=24 o hours=168 (7 dias).

    Si la estacion ya tiene lecturas reales del sensor, se arma la serie
    a partir de esas lecturas (acumuladas desde que el sensor empezo a
    postear). Mientras no haya suficiente historial real todavia, se
    devuelve la serie simulada como antes.
    """
    if hours not in (24, 168):
        raise HTTPException(status_code=400, detail="hours debe ser 24 o 168")
    real_points = sensor.get_real_history(station_id, hours=hours)
    if real_points is not None:
        points = real_points
        source = "sensor"
    else:
        try:
            points = simulator.get_history(station_id, hours=hours)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        source = "simulated"
    return {
        "station_id": station_id,
        "hours": hours,
        "source": source,
        "points": points,
        "min": min(p["level_m"] for p in points),
        "max": max(p["level_m"] for p in points),
        "avg": round(sum(p["level_m"] for p in points) / len(points), 2),
    }


# ---------------------------------------------------------------------------
# Mapa / estaciones
# ---------------------------------------------------------------------------

@app.get("/api/stations")
def stations():
    """Resumen de todas las estaciones con su ubicacion y nivel actual."""
    result = simulator.get_stations_summary()
    for s in result:
        if sensor.has_real_data(s["station_id"]):
            real = sensor.get_last_sensor_reading(s["station_id"])
            s["level_m"] = real["level_m"]
            s["source"] = "sensor"
        s["status"] = thresholds.status_from_level(s["level_m"])
    return result


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------

@app.get("/api/notifications")
def list_notifications():
    return notifications.get_notifications()


@app.post("/api/notifications", status_code=201)
def create_notification(payload: NotificationCreate):
    """Crear una notificacion manual (util para simular una alerta en la demo)."""
    return notifications.add_notification(payload.type, payload.text)


# ---------------------------------------------------------------------------
# Configuracion de umbrales
# ---------------------------------------------------------------------------

@app.get("/api/config/thresholds")
def get_thresholds():
    return thresholds.get_thresholds()


@app.put("/api/config/thresholds")
def update_thresholds(payload: ThresholdsUpdate):
    try:
        return thresholds.set_thresholds(payload.atencion, payload.evacuacion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
