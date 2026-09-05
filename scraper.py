"""
Lee canales públicos de Telegram usando la vista web de solo lectura
en https://t.me/s/<canal>, que no requiere autenticación.

Esto es intencionalmente simple (requests + BeautifulSoup) para no
depender de una cuenta de Telegram propia (que se podría banear/limitar).
Si en el futuro necesitas más volumen o canales privados, la alternativa
es Telethon/Pyrogram con una cuenta dedicada.
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
from dateutil import parser as dateparser

from config import HTTP_USER_AGENT


@dataclass
class MensajeCrudo:
    canal: str
    message_id: str  # ej. "EmpresaElectricaDeLaHabana/12345"
    texto: str
    fecha: datetime


def _limpiar_texto(nodo) -> str:
    """
    Convierte el contenido HTML del mensaje a texto plano, respetando
    saltos de línea (Telegram usa <br> dentro del div del mensaje).
    """
    for br in nodo.find_all("br"):
        br.replace_with("\n")
    return nodo.get_text().strip()


def obtener_mensajes(canal: str, limite: int = 20) -> list[MensajeCrudo]:
    """
    Descarga los mensajes más recientes de un canal público.
    Devuelve una lista ordenada del más antiguo al más reciente,
    igual que aparecen en la página.
    """
    url = f"https://t.me/s/{canal}"
    headers = {"User-Agent": HTTP_USER_AGENT}

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    mensajes = []

    for wrap in soup.select("div.tgme_widget_message_wrap"):
        msg_div = wrap.select_one("div.tgme_widget_message")
        if msg_div is None:
            continue

        message_id = msg_div.get("data-post")  # "canal/12345"
        if not message_id:
            continue

        texto_div = msg_div.select_one("div.tgme_widget_message_text")
        if texto_div is None:
            # Puede ser un mensaje solo con imagen/video, sin texto: se ignora.
            continue
        texto = _limpiar_texto(texto_div)

        time_tag = msg_div.select_one("time.tgme_widget_message_date time")
        if time_tag is None or not time_tag.get("datetime"):
            continue
        fecha = dateparser.isoparse(time_tag["datetime"])

        mensajes.append(
            MensajeCrudo(
                canal=canal,
                message_id=message_id,
                texto=texto,
                fecha=fecha,
            )
        )

    return mensajes[-limite:]


if __name__ == "__main__":
    # Prueba manual rápida: python scraper.py <canal>
    import sys

    canal_prueba = sys.argv[1] if len(sys.argv) > 1 else "EmpresaElectricaDeLaHabana"
    for m in obtener_mensajes(canal_prueba, limite=5):
        print("=" * 60)
        print(m.fecha, m.message_id)
        print(m.texto[:300])
