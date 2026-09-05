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

Sensor ultrasónico (HC-SR04) instalado en la base del puente, apuntando
hacia abajo, conectado a un **ESP32** (no "CPL32" — fue una confusión de
nombre). El ESP32 mide sobre una maqueta a escala (altura de la maqueta:
0.15 m) y escala el resultado a metros "reales" (altura real simulada:
15 m) **a bordo, antes de mandar el dato**:

```
nivelMaqueta = ALTURA_MAQUETA - distancia_medida       (0 a 0.15 m)
nivelReal    = nivelMaqueta * ALTURA_REAL / ALTURA_MAQUETA   (0 a 15 m)
```

Este backend **no recibe la distancia cruda** — recibe el nivel ya
calculado por el firmware (ver `app/sensor.py`, `record_sensor_reading`).

## Conectividad

- Sensor ultrasónico (HC-SR04) → **ESP32** → WiFi → backend
- El ESP32 se conecta a un WiFi (hoy, el hotspot de un celular, red
  privada) y por defecto solo sirve datos en su propia IP local
  (`GET /nivel`) — no los envía a nadie
- Como este backend corre en internet, fuera de esa red privada, el
  firmware hace además un **POST periódico** hacia `/api/sensor/reading`
  con su lectura — así el ESP32 empuja el dato en vez de esperar que
  alguien se lo pida

## Conectar el sensor real

El punto de entrada es:

```
POST /api/sensor/reading
Content-Type: application/json

{ "station_id": "km42", "nivel": 3.30, "alerta": "Normal" }
```

Es el **mismo JSON que ya devuelve el propio endpoint del ESP32**
(`GET /nivel`), más el `station_id`. El campo `nivel` es el nivel en
metros ya calculado por el firmware (0 a 15) — este backend no vuelve a
convertir nada, solo guarda el dato y recalcula el `status` con los
umbrales configurados acá (por si difieren de los que tenga el firmware
hardcodeados). El campo `alerta` es opcional/informativo.

A partir de esa llamada, `/api/reading/current`, `/api/reading/all` y
`/api/stations` devuelven ese dato real para esa estación en lugar del
simulado, y `/api/history` empieza a construir su serie a partir de las
lecturas reales acumuladas (antes de la primera lectura real, sigue
devolviendo la serie simulada).

**Importante — el ESP32 debe apuntar a la URL pública de Render**
(`https://rio-alerta-backend.onrender.com/api/sensor/reading`), no a una
IP local, y la red WiFi del ESP32 necesita salida a internet.

**Consultar la última lectura real** (útil para debug):
```
GET /api/sensor/reading?station_id=km42
```

## Persistencia — pendiente para producción

Las lecturas del sensor, el historial derivado, los umbrales y las
notificaciones viven en memoria (variables Python), no en base de
datos. Esto significa que si Render reinicia el proceso (redeploy, o
el propio proceso cae) se pierde todo y la app vuelve a arrancar con
los valores simulados/por defecto hasta que el sensor mande una lectura
nueva. Para dejarlo estable en producción, migrar a una base de datos
(aunque sea SQLite) es el siguiente paso — el plan free de Render
"duerme" el servicio tras inactividad, pero **no** reinicia el proceso
solo por eso, así que el impacto real es más bajo de lo que parece;
igual conviene no depender de la memoria a mediano plazo.

## Endpoints principales

| Endpoint | Descripción |
|---|---|
| `POST /api/sensor/reading` | Ingesta de lectura del sensor (nivel ya calculado por el ESP32) |
| `GET /api/sensor/reading?station_id=km42` | Última lectura real recibida |
| `GET /api/reading/current?station_id=km42` | Lectura actual (real si existe, si no simulada), con status |
| `GET /api/reading/all` | Lectura actual de todas las estaciones |
| `GET /api/history?station_id=km42&hours=24` | Serie histórica (real si hay lecturas del sensor, si no simulada; 24 o 168 horas) |
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
