"""
Notificaciones/avisos generados por el sistema.

Guardadas en memoria para la demo. En produccion esto seria una
tabla en base de datos, y la creacion de alertas por umbral se
dispararia desde un job/worker que lee el medidor en tiempo real,
no desde el propio endpoint GET como se simplifica aca.
"""

from datetime import datetime, timedelta

_notifications = [
    {
        "id": 1,
        "type": "warning",
        "text": "Caudal superó el umbral de atención (150 m³/s)",
        "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
    },
    {
        "id": 2,
        "type": "info",
        "text": "Lluvia intensa reportada aguas arriba",
        "timestamp": (datetime.utcnow() - timedelta(hours=4, minutes=30)).isoformat() + "Z",
    },
    {
        "id": 3,
        "type": "success",
        "text": "Nivel normalizado tras lluvias de ayer",
        "timestamp": (datetime.utcnow() - timedelta(days=1, hours=4)).isoformat() + "Z",
    },
    {
        "id": 4,
        "type": "info",
        "text": "Mantenimiento programado en estación Km 18",
        "timestamp": (datetime.utcnow() - timedelta(days=1, hours=14)).isoformat() + "Z",
    },
]

_next_id = 5


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
