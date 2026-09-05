"""
Envía notificaciones push a los topics de FCM cuando el worker detecta
un parte nuevo. Usa el mismo esquema de topics que el frontend Flutter:
    nacional
    provincia_<slug>
    municipio_<slug>

Requiere el JSON de credenciales de una cuenta de servicio de Firebase
(ver config.FIREBASE_CREDENTIALS_PATH). Si el archivo no existe, esto
funciona en modo "no-op" (loguea pero no falla) para que puedas seguir
desarrollando el resto del backend sin tener Firebase listo todavía.
"""

import os
import re
import json
import logging

from config import FIREBASE_CREDENTIALS_PATH

logger = logging.getLogger("fcm")

_firebase_app = None
_firebase_disponible = False

try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    _credenciales_json_env = os.environ.get("FIREBASE_CREDENTIALS_JSON")

    if _credenciales_json_env:
        # Opción recomendada para Railway: pegar el contenido completo del
        # JSON de la cuenta de servicio como variable de entorno, sin
        # necesidad de subir un archivo aparte.
        cred = credentials.Certificate(json.loads(_credenciales_json_env))
        _firebase_app = firebase_admin.initialize_app(cred)
        _firebase_disponible = True
    elif os.path.exists(FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
        _firebase_disponible = True
    else:
        logger.warning(
            "No se encontró configuración de Firebase (ni FIREBASE_CREDENTIALS_JSON "
            "ni el archivo %s): las notificaciones push quedarán deshabilitadas "
            "(modo no-op) hasta que la agregues.",
            FIREBASE_CREDENTIALS_PATH,
        )
except ImportError:
    logger.warning("firebase_admin no está instalado; notificaciones en modo no-op.")


def normalizar_topic(valor: str) -> str:
    """Debe producir el MISMO resultado que NotificationService.normalizeTopic
    del lado de Flutter, o las suscripciones no van a coincidir."""
    reemplazos = str.maketrans("áéíóúñ", "aeioun")
    valor = valor.lower().translate(reemplazos)
    valor = re.sub(r"[^a-z0-9]+", "_", valor)
    return valor.strip("_")


def enviar_a_topic(topic: str, titulo: str, cuerpo: str):
    if not _firebase_disponible:
        logger.info("[no-op] Push a '%s': %s - %s", topic, titulo, cuerpo)
        return

    mensaje = messaging.Message(
        notification=messaging.Notification(title=titulo, body=cuerpo),
        topic=topic,
    )
    try:
        messaging.send(mensaje)
    except Exception:
        logger.exception("Error enviando push al topic %s", topic)


def notificar_parte_nuevo(*, provincia: str, municipio: str | None, tipo: str, resumen: str):
    if tipo == "general_nacional":
        enviar_a_topic("nacional", "Parte eléctrico nacional", resumen)
        return

    titulo = "Corte de servicio" if tipo == "corte" else "Servicio restablecido"
    enviar_a_topic(f"provincia_{normalizar_topic(provincia)}", titulo, resumen)
    if municipio:
        enviar_a_topic(f"municipio_{normalizar_topic(municipio)}", titulo, resumen)
