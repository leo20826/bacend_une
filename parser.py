"""
Parser de mensajes de la empresa eléctrica.

Estrategia (como se discutió): los emojis actúan como delimitadores
mucho más estables que el texto libre alrededor, así que clasificamos
primero por emojis/palabras clave, y luego extraemos campos con regex
dentro de cada tipo ya clasificado.

Filosofía de "fallback seguro": si un mensaje no matchea ningún patrón
conocido, se devuelve como SIN_CLASIFICAR pero el texto crudo se conserva
siempre completo, para no perder información aunque cambie el formato.
"""

import re
from dataclasses import dataclass, field


TIPO_CORTE = "corte"
TIPO_RESTABLECIMIENTO = "restablecimiento"
TIPO_GENERAL_NACIONAL = "general_nacional"
TIPO_SIN_CLASIFICAR = "sin_clasificar"

# Regex para extraer pares (codigo_circuito, zonas) usando 👉 como separador.
# Ej: "👉D631: Calle 23 entre Paseo y G, Vedado"
_RE_CIRCUITO = re.compile(r"👉\s*([A-ZÁÉÍÓÚÑ0-9]+)\s*:?\s*([^👉\n]+)")

_RE_SUBESTACION = re.compile(
    r"SUBESTACI[ÓO]N\s+(?:DE\s+)?([A-ZÁÉÍÓÚÑ0-9 ]+?)(?:,|\.|$)",
    re.IGNORECASE,
)

_RE_MUNICIPIOS = re.compile(
    r"municipios?\s+(?:de\s+)?(.+?)\s+pertenecientes?",
    re.IGNORECASE | re.DOTALL,
)

_RE_HORA = re.compile(r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)")

_RE_DEFICIT = re.compile(r"d[ée]ficit\D{0,15}?(\d+(?:[.,]\d+)?)\s*MW", re.IGNORECASE)
_RE_DISPONIBILIDAD = re.compile(
    r"disponibilidad\D{0,15}?(\d+(?:[.,]\d+)?)\s*MW", re.IGNORECASE
)
_RE_DEMANDA = re.compile(r"demanda\D{0,15}?(\d+(?:[.,]\d+)?)\s*MW", re.IGNORECASE)


@dataclass
class CircuitoAfectado:
    codigo: str
    zonas: str


@dataclass
class ParteParseado:
    tipo: str
    texto_crudo: str
    subestacion: str | None = None
    municipios_texto: str | None = None
    hora_restablecimiento: str | None = None
    circuitos: list[CircuitoAfectado] = field(default_factory=list)
    deficit_mw: float | None = None
    disponibilidad_mw: float | None = None
    demanda_mw: float | None = None


def _clasificar(texto: str) -> str:
    t = texto.lower()

    # Señal de parte general nacional: cifras explícitas de MW (déficit,
    # disponibilidad o demanda), y que NO mencione circuitos/municipios
    # puntuales (para no confundirlo con un aviso local que solo dice
    # "por déficit de generación" como causa, sin cifras numéricas).
    tiene_cifras_mw = bool(
        _RE_DEFICIT.search(texto)
        or _RE_DISPONIBILIDAD.search(texto)
        or _RE_DEMANDA.search(texto)
    )
    if tiene_cifras_mw and "circuito" not in t and "municipio" not in t:
        return TIPO_GENERAL_NACIONAL

    # Señales de RESTABLECIMIENTO (el servicio ya fue reparado/normalizado).
    # Se revisan ANTES que las de corte para que frases como "queda
    # reparada" no caigan por error en las señales de corte de abajo.
    palabras_restablecido = (
        "restablecido", "restablecimiento", "restablece", "queda repara",
        "quedó reparad", "reparada", "reparado", "resuelta la avería",
        "resuelta la averia", "solucionada", "normalizado el servicio",
        "con servicio eléctrico", "con servicio electrico",
    )
    if any(p in t for p in palabras_restablecido):
        return TIPO_RESTABLECIMIENTO

    # Señales de CORTE: el vocabulario real del canal es más variado que
    # solo "🛑circuitos afectados" — incluye avisos de disparo, avería,
    # afectación puntual, déficit de generación como causa, manipulación
    # (trabajos/mantenimiento) que deja el circuito sin servicio, etc.
    palabras_corte = (
        "circuitos afectados", "se afecta", "se afectó", "afecta el servicio",
        "afectan por disparo", "afectado por disparo", "disparo del circuito",
        "disparo automático", "disparo automatico", "por avería", "por averia",
        "déficit de generación", "deficit de generacion",
        "por manipulación", "por manipulacion", "afectado por manipulación",
    )
    if "🛑" in texto or any(p in t for p in palabras_corte):
        return TIPO_CORTE

    if (
        "⚠️" in texto or "⚡" in texto or "🚨" in texto or "🚧" in texto
        or "🛠️" in texto
    ):
        # Tiene emojis típicos de aviso pero no matcheó ninguna frase
        # conocida arriba; se trata como corte por defecto (es el caso
        # más común en este canal), pero el texto crudo queda disponible
        # siempre para revisión manual si el default resulta incorrecto.
        return TIPO_CORTE

    return TIPO_SIN_CLASIFICAR


def _extraer_circuitos(texto: str) -> list[CircuitoAfectado]:
    circuitos = []
    for match in _RE_CIRCUITO.finditer(texto):
        codigo = match.group(1).strip()
        zonas = match.group(2).strip().rstrip(".,")
        if codigo and zonas:
            circuitos.append(CircuitoAfectado(codigo=codigo, zonas=zonas))
    return circuitos


def _a_float(valor: str | None) -> float | None:
    if valor is None:
        return None
    return float(valor.replace(",", "."))


def parse_mensaje(texto: str) -> ParteParseado:
    tipo = _clasificar(texto)
    parte = ParteParseado(tipo=tipo, texto_crudo=texto)

    if tipo in (TIPO_CORTE, TIPO_RESTABLECIMIENTO):
        parte.circuitos = _extraer_circuitos(texto)

        m_sub = _RE_SUBESTACION.search(texto)
        if m_sub:
            parte.subestacion = m_sub.group(1).strip()

        m_mun = _RE_MUNICIPIOS.search(texto)
        if m_mun:
            parte.municipios_texto = m_mun.group(1).strip()

        if tipo == TIPO_RESTABLECIMIENTO:
            m_hora = _RE_HORA.search(texto)
            if m_hora:
                parte.hora_restablecimiento = m_hora.group(1).strip()

    elif tipo == TIPO_GENERAL_NACIONAL:
        m = _RE_DEFICIT.search(texto)
        parte.deficit_mw = _a_float(m.group(1)) if m else None
        m = _RE_DISPONIBILIDAD.search(texto)
        parte.disponibilidad_mw = _a_float(m.group(1)) if m else None
        m = _RE_DEMANDA.search(texto)
        parte.demanda_mw = _a_float(m.group(1)) if m else None

    return parte
