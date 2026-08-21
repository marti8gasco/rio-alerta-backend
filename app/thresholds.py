"""
Logica de umbrales de alerta.

Un solo lugar que decide "normal / atencion / evacuacion" a partir
del NIVEL del río (metros sobre el cauce normal), no de caudal.

Se descartó medir caudal: el sensor solo mide nivel, y nivel y
caudal no son proporcionales entre sí (dependen de la geometría del
cauce y otros factores hidrológicos). El nivel es la métrica que se
usa en la práctica (ver boletines del CECOED San José).

El frontend tiene la misma logica duplicada (statusFromLevel en
rio-alerta-app.jsx) — al conectar la app real al backend, el
frontend deberia consumir el status que devuelve la API en vez de
calcularlo el mismo, para no tener dos fuentes de verdad.
"""

# Valores por defecto (metros sobre el cauce normal); configurables
# via PUT /config/thresholds. Estos son los mismos umbrales que ya
# vienen calculados en el firmware del ESP32 (ver handleNivel() en
# el .ino): 5 m = amarilla/precaución, 7 m = roja/evacuar.
_thresholds = {
    "atencion": 5.0,
    "evacuacion": 7.0,
}


def get_thresholds() -> dict:
    return dict(_thresholds)


def set_thresholds(atencion: float, evacuacion: float) -> dict:
    if atencion >= evacuacion:
        raise ValueError("El umbral de atencion debe ser menor al de evacuacion")
    _thresholds["atencion"] = atencion
    _thresholds["evacuacion"] = evacuacion
    return get_thresholds()


def status_from_level(level_m: float) -> str:
    if level_m >= _thresholds["evacuacion"]:
        return "evacuacion"
    if level_m >= _thresholds["atencion"]:
        return "atencion"
    return "normal"
