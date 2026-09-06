"""
Loop principal del backend. Cada INTERVALO_POLLING_SEGUNDOS:
  1. Revisa cada canal configurado.
  2. Descarta mensajes ya procesados (tabla mensajes_procesados).
  3. Parsea los nuevos.
  4. Guarda en la tabla `partes`, asociado a la provincia del canal.
  5. Publica push al topic de la provincia (y al nacional si aplica).

Corre esto con: python worker.py
En producción, esto debería vivir en un proceso persistente (systemd,
Docker, un servicio en la nube), no solo lanzarse manualmente.
"""

import time
import logging

from config import (
    CANALES_POR_PROVINCIA,
    CANALES_PARTE_NACIONAL,
    INTERVALO_POLLING_SEGUNDOS,
)
from scraper import obtener_mensajes
from parser import parse_mensaje, TIPO_GENERAL_NACIONAL
import db
import fcm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("worker")


def _resumen_para_notificacion(parte) -> str:
    if parte.tipo == TIPO_GENERAL_NACIONAL:
        partes_txt = []
        if parte.disponibilidad_mw is not None:
            partes_txt.append(f"disponibilidad {parte.disponibilidad_mw:.0f} MW")
        if parte.deficit_mw is not None:
            partes_txt.append(f"déficit {parte.deficit_mw:.0f} MW")
        return ", ".join(partes_txt) or parte.texto_crudo[:120]

    if parte.circuitos:
        codigos = ", ".join(c.codigo for c in parte.circuitos[:5])
        return f"Circuitos: {codigos}"
    return parte.texto_crudo[:120]


def _procesar_canal(canal: str, provincia: str | None):
    try:
        mensajes = obtener_mensajes(canal, limite=20)
    except Exception:
        logger.exception("Error obteniendo mensajes del canal %s", canal)
        return

    nuevos = 0
    for msg in mensajes:
        if db.ya_procesado(msg.message_id):
            continue
        nuevos += 1

        parte = parse_mensaje(msg.texto)
        provincia_del_parte = (
            "Nacional" if parte.tipo == TIPO_GENERAL_NACIONAL else provincia
        )

        db.guardar_parte(
            id_=msg.message_id,
            canal=canal,
            provincia=provincia_del_parte,
            municipio=None,
            tipo=parte.tipo,
            fecha=msg.fecha,
            texto_crudo=parte.texto_crudo,
            subestacion=parte.subestacion,
            circuitos=[
                {"codigo": c.codigo, "zonas": c.zonas} for c in parte.circuitos
            ],
            deficit_mw=parte.deficit_mw,
            disponibilidad_mw=parte.disponibilidad_mw,
            demanda_mw=parte.demanda_mw,
        )

        fcm.notificar_parte_nuevo(
            provincia=provincia_del_parte,
            tipo=parte.tipo,
            resumen=_resumen_para_notificacion(parte),
        )

        logger.info(
            "Guardado parte %s (%s) tipo=%s",
            msg.message_id, provincia_del_parte, parte.tipo,
        )

        db.marcar_procesado(canal, msg.message_id)

    logger.info(
        "Canal %s: %d mensajes revisados, %d nuevos procesados.",
        canal, len(mensajes), nuevos,
    )


def ciclo_una_vez():
    for canal, provincia in CANALES_POR_PROVINCIA.items():
        _procesar_canal(canal, provincia)
    for canal in CANALES_PARTE_NACIONAL:
        _procesar_canal(canal, provincia=None)


def correr_loop():
    db.init_db()
    logger.info(
        "Worker iniciado. Revisando %d canal(es) de provincia + %d nacional(es) "
        "cada %d segundos.",
        len(CANALES_POR_PROVINCIA),
        len(CANALES_PARTE_NACIONAL),
        INTERVALO_POLLING_SEGUNDOS,
    )
    while True:
        try:
            ciclo_una_vez()
        except Exception:
            logger.exception("Error inesperado en el ciclo del worker")
        time.sleep(INTERVALO_POLLING_SEGUNDOS)


if __name__ == "__main__":
    correr_loop()
