"""
Notificaciones/avisos generados por el sistema.

Guardadas en memoria para la demo. En produccion esto seria una
tabla en base de datos, y la creacion de alertas por umbral se
dispararia desde un job/worker que lee el medidor en tiempo real,
no desde el propio endpoint GET como se simplifica aca.
"""

from datetime import datetime, timedelta


# Notificacion de ejemplo minima y neutra — el frontend ya arma sus propios
# avisos de nivel/tendencia/lluvia a partir de los datos reales vigentes
# (ver HidroTecApp en el frontend), asi que aca solo dejamos algo generico
# que no contradiga esos numeros (antes habia avisos fijos que mencionaban
# "caudal" y umbrales/estaciones que ya no existen en la app).
_notifications = [
    {
        "id": 1,
        "type": "info",
        "text": "Sensor de Km 95 reportando con normalidad",
        "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
    },
]

_next_id = 2


def get_notifications() -> list[dict]:
    return sorted(_notifications, key=lambda n: n["timestamp"], reverse=True)


def add_notification(notif_type: str, text: str) -> dict:
    global _next_id
    notif = {
        "id": _next_id,
        "type": notif_type,
        "text": text,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    _notifications.append(notif)
    _next_id += 1
    return notif
