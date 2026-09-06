"""
Capa de acceso a datos, usando Postgres (pensado para el free tier de
Neon.tech, ver DEPLOY_FREE.md).

Se migró de SQLite a Postgres porque las plataformas de hosting gratuitas
(Render, por ejemplo) NO garantizan disco persistente en su plan free:
el archivo SQLite se perdería cada vez que el servicio se "duerme" y
despierta. Postgres externo (Neon) resuelve esto sin costo.

Las funciones públicas (guardar_parte, obtener_partes_por_zona, etc.)
mantienen la misma firma que la versión anterior con SQLite, así que
worker.py y api.py no necesitan cambios.
"""

import os
import json
from contextlib import contextmanager
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")


def init_db():
    if not DATABASE_URL:
        raise RuntimeError(
            "Falta la variable de entorno DATABASE_URL (connection string "
            "de Postgres, ej. la que te da Neon.tech). Ver DEPLOY_FREE.md."
        )
    with _conectar() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mensajes_procesados (
                    canal TEXT NOT NULL,
                    message_id TEXT NOT NULL PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS partes (
                    id TEXT PRIMARY KEY,
                    canal TEXT NOT NULL,
                    provincia TEXT NOT NULL,
                    municipio TEXT,
                    tipo TEXT NOT NULL,
                    fecha TIMESTAMP NOT NULL,
                    texto_crudo TEXT NOT NULL,
                    subestacion TEXT,
                    circuitos_json TEXT,
                    deficit_mw DOUBLE PRECISION,
                    disponibilidad_mw DOUBLE PRECISION,
                    demanda_mw DOUBLE PRECISION,
                    creado_en TIMESTAMP NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_partes_provincia
                    ON partes (provincia, fecha DESC);
                CREATE INDEX IF NOT EXISTS idx_partes_tipo
                    ON partes (tipo, fecha DESC);
                """
            )


@contextmanager
def _conectar():
    con = psycopg.connect(DATABASE_URL)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def ya_procesado(message_id: str) -> bool:
    with _conectar() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM mensajes_procesados WHERE message_id = %s",
                (message_id,),
            )
            return cur.fetchone() is not None


def marcar_procesado(canal: str, message_id: str):
    with _conectar() as con:
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO mensajes_procesados (canal, message_id) "
                "VALUES (%s, %s) ON CONFLICT (message_id) DO NOTHING",
                (canal, message_id),
            )


def guardar_parte(
    *,
    id_: str,
    canal: str,
    provincia: str,
    municipio: str | None,
    tipo: str,
    fecha: datetime,
    texto_crudo: str,
    subestacion: str | None,
    circuitos: list[dict],
    deficit_mw: float | None,
    disponibilidad_mw: float | None,
    demanda_mw: float | None,
):
    with _conectar() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO partes (
                    id, canal, provincia, municipio, tipo, fecha, texto_crudo,
                    subestacion, circuitos_json, deficit_mw, disponibilidad_mw,
                    demanda_mw, creado_en
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    canal = EXCLUDED.canal,
                    provincia = EXCLUDED.provincia,
                    municipio = EXCLUDED.municipio,
                    tipo = EXCLUDED.tipo,
                    fecha = EXCLUDED.fecha,
                    texto_crudo = EXCLUDED.texto_crudo,
                    subestacion = EXCLUDED.subestacion,
                    circuitos_json = EXCLUDED.circuitos_json,
                    deficit_mw = EXCLUDED.deficit_mw,
                    disponibilidad_mw = EXCLUDED.disponibilidad_mw,
                    demanda_mw = EXCLUDED.demanda_mw
                """,
                (
                    id_,
                    canal,
                    provincia,
                    municipio,
                    tipo,
                    fecha,
                    texto_crudo,
                    subestacion,
                    json.dumps(circuitos, ensure_ascii=False),
                    deficit_mw,
                    disponibilidad_mw,
                    demanda_mw,
                    datetime.utcnow(),
                ),
            )


def _row_a_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "provincia": row["provincia"],
        "municipio": row["municipio"],
        "tipo": row["tipo"],
        "fecha": row["fecha"].isoformat() if row["fecha"] else None,
        "texto_crudo": row["texto_crudo"],
        "subestacion": row["subestacion"],
        "circuitos": json.loads(row["circuitos_json"] or "[]"),
        "deficit_mw": row["deficit_mw"],
        "disponibilidad_mw": row["disponibilidad_mw"],
        "demanda_mw": row["demanda_mw"],
    }


def obtener_parte_general_mas_reciente() -> dict | None:
    with _conectar() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM partes WHERE tipo = 'general_nacional' "
                "ORDER BY fecha DESC LIMIT 1"
            )
            row = cur.fetchone()
            return _row_a_dict(row) if row else None


def obtener_partes_por_provincia(provincia: str, limite: int = 20) -> list[dict]:
    """
    Últimos `limite` partes de una provincia (excluyendo el parte general
    nacional, que se consulta aparte con obtener_parte_general_mas_reciente).
    """
    with _conectar() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM partes
                WHERE provincia = %s AND tipo != 'general_nacional'
                ORDER BY fecha DESC LIMIT %s
                """,
                (provincia, limite),
            )
            return [_row_a_dict(r) for r in cur.fetchall()]
