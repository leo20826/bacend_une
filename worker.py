"""
Loop principal del backend. Cada INTERVALO_POLLING_SEGUNDOS:
  1. Revisa cada canal configurado.
  2. Descarta mensajes ya procesados (tabla mensajes_procesados).
  3. Parsea los nuevos.
  4. Detecta qué municipio(s) menciona (si aplica).
  5. Guarda en la tabla `partes` (una fila por municipio detectado,
     o una sola fila con municipio=NULL si no se detectó ninguno,
     lo que significa "aplica a toda la provincia").
  6. Publica push a los topics correspondientes.

Corre esto con: python worker.py
En producción, esto debería vivir en un proceso persistente (systemd,
Docker, un servicio en la nube), no solo lanzarse manualmente.
"""

import time
import logging
import uuid

from config import (
    CANALES_POR_PROVINCIA,
    CANALES_PARTE_NACIONAL,
    INTERVALO_POLLING_SEGUNDOS,
)
from scraper import obtener_mensajes
from parser import parse_mensaje, TIPO_GENERAL_NACIONAL
from municipios_cuba import detectar_municipios
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

        if parte.tipo == TIPO_GENERAL_NACIONAL:
            _guardar_y_notificar(
                parte=parte,
                canal=canal,
                provincia="Nacional",
                municipio=None,
                fecha=msg.fecha,
                message_id=msg.message_id,
            )
        else:
            municipios_detectados = (
                detectar_municipios(provincia, msg.texto) if provincia else []
            )
            if municipios_detectados:
                for municipio in municipios_detectados:
                    _guardar_y_notificar(
                        parte=parte,
                        canal=canal,
                        provincia=provincia,
                        municipio=municipio,
                        fecha=msg.fecha,
                        message_id=msg.message_id,
                        sufijo_id=municipio,
                    )
            else:
                # No se detectó municipio específico: aplica a toda la
                # provincia (mejor mostrarlo igual que perder el dato).
                _guardar_y_notificar(
                    parte=parte,
                    canal=canal,
                    provincia=provincia,
                    municipio=None,
                    fecha=msg.fecha,
                    message_id=msg.message_id,
                )

        db.marcar_procesado(canal, msg.message_id)

    logger.info(
        "Canal %s: %d mensajes revisados, %d nuevos procesados.",
        canal, len(mensajes), nuevos,
    )


def _guardar_y_notificar(
    *, parte, canal, provincia, municipio, fecha, message_id, sufijo_id=None
):
    id_parte = f"{message_id}_{sufijo_id}" if sufijo_id else message_id

    db.guardar_parte(
        id_=id_parte,
        canal=canal,
        provincia=provincia,
        municipio=municipio,
        tipo=parte.tipo,
        fecha=fecha,
        texto_crudo=parte.texto_crudo,
        subestacion=parte.subestacion,
        circuitos=[{"codigo": c.codigo, "zonas": c.zonas} for c in parte.circuitos],
        deficit_mw=parte.deficit_mw,
        disponibilidad_mw=parte.disponibilidad_mw,
        demanda_mw=parte.demanda_mw,
    )

    fcm.notificar_parte_nuevo(
        provincia=provincia,
        municipio=municipio,
        tipo=parte.tipo,
        resumen=_resumen_para_notificacion(parte),
    )

    logger.info(
        "Guardado parte %s (%s / %s) tipo=%s",
        id_parte, provincia, municipio or "-", parte.tipo,
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
