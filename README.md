# RioAlerta — backend

API para el sistema de monitoreo de **nivel** de río (metros sobre
el cauce normal). No mide caudal: el sensor instalado no lo mide
directamente, y nivel y caudal no son proporcionales entre sí
(dependen de la geometría del cauce y otros factores hidrológicos).

## Correr localmente

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000`. Documentación interactiva
(Swagger) en `http://localhost:8000/docs`.

## Cómo funciona el sensor

Sensor ultrasónico instalado en la base del puente, apuntando hacia
abajo. Mide **distancia** al agua (no nivel directamente), con rango
de 0 a 12 metros.

La lectura es inversa al nivel del río:

| Situación         | Distancia medida | Nivel de agua |
|--------------------|-------------------|----------------|
| Sin crecida         | 12 m              | 0 m            |
| Río sube 4 m        | 8 m               | 4 m            |
| Río sube 6 m        | 6 m               | 6 m            |

Conversión: `nivel_m = 12 - distancia_medida_m` (ver `app/sensor.py`,
función `level_from_distance`).

## Conectividad

- Sensor ultrasónico → placa **CPL32** → **WiFi** → backend
- El sensor ya está instalado y operativo (estación Km 42)
- Aún no confirmado si la placa hace POST HTTP directo o si hay un
  gateway/broker (ej. MQTT) en el medio — ver sección siguiente

## Conectar el sensor real

El punto de entrada es:

```
POST /api/sensor/reading
Content-Type: application/json

{ "station_id": "km42", "distance_m": 8.7 }
```

Se manda la **distancia cruda** medida por el sensor (no el nivel
calculado) — el backend hace la conversión y guarda el resultado.
A partir de esa llamada, `/api/reading/current`, `/api/reading/all`
y `/api/stations` devuelven ese dato real para esa estación en lugar
del dato simulado.

**Si la placa CPL32 puede hacer HTTP directo:** apuntarla a este
endpoint (`POST /api/sensor/reading`) con el body de arriba cada vez
que tome una lectura.

**Si hay un gateway o broker MQTT en el medio** (lo más común en
placas tipo ESP32/CPL32 — publican a un broker y no hacen HTTP
directo): agregar un pequeño proceso que se suscriba al tópico MQTT
correspondiente y, por cada mensaje, haga el POST HTTP de arriba (o
llame directo a `sensor.record_sensor_reading(station_id, distance_m)`
si ese proceso corre en el mismo backend). Es un puente MQTT → HTTP
de unas pocas líneas; avisar cuando esté confirmado el modo de envío
de la placa para armarlo.

**Consultar la última lectura real** (útil para debug):
```
GET /api/sensor/reading?station_id=km42
```

## Endpoints principales

| Endpoint | Descripción |
|---|---|
| `POST /api/sensor/reading` | Ingesta de lectura cruda del sensor (distancia) |
| `GET /api/sensor/reading?station_id=km42` | Última lectura real recibida |
| `GET /api/reading/current?station_id=km42` | Lectura actual (real si existe, si no simulada), con status |
| `GET /api/reading/all` | Lectura actual de todas las estaciones |
| `GET /api/history?station_id=km42&hours=24` | Serie histórica simulada (24 o 168 horas) |
| `GET /api/stations` | Resumen de estaciones para el mapa |
| `GET /api/notifications` | Lista de notificaciones |
| `POST /api/notifications` | Crear notificación manual (para simular alertas en demo) |
| `GET /api/config/thresholds` | Umbrales actuales (metros) |
| `PUT /api/config/thresholds` | Actualizar umbrales |

## Conectar el frontend

En `rio-alerta-app.jsx` / la versión standalone, reemplazar las
constantes simuladas (`HISTORY_24H`, `STATIONS`, `NOTIFICATIONS`,
etc) por `fetch()` a estos endpoints. Los shapes de datos ya están
pensados para calzar con lo que la UI espera (`level_m` en vez del
`flow`/`caudal` anterior).
