"""
API REST + worker de scraping en un solo proceso.

Pensado para desplegarse como UN SOLO servicio en plataformas tipo Railway/
Render (un solo comando de arranque, un solo volumen de almacenamiento).
El scraping de Telegram corre como una tarea en segundo plano dentro del
mismo proceso de la API, en vez de ser un proceso aparte.

Endpoints pensados para calzar directo con
lib/services/api_service.dart del frontend Flutter:

  GET /api/parte-general
  GET /api/partes?provincia=X

Correr con: uvicorn api:app --host 0.0.0.0 --port 8000
(en Railway, el puerto lo da la variable de entorno $PORT, ver DEPLOY_RAILWAY.md)
"""

import asyncio
import os
import logging

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import db
import worker
from config import INTERVALO_POLLING_SEGUNDOS

logger = logging.getLogger("api")

# Token para proteger /api/scrape-now. Si no se configura, el endpoint queda
# deshabilitado (devuelve 403 siempre) para no dejarlo abierto por accidente.
SCRAPE_TOKEN = os.environ.get("SCRAPE_TOKEN")

app = FastAPI(title="API Partes Eléctricos Cuba")

# CORS abierto para desarrollo. En producción, restringir a los dominios
# reales que consuman la API si sirves algo desde web.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_tarea_worker: asyncio.Task | None = None


async def _loop_worker_en_segundo_plano():
    """
    Corre el mismo ciclo de worker.py, pero como tarea async dentro del
    proceso de la API. Usamos asyncio.to_thread porque el scraping
    (requests, BeautifulSoup, SQLite) es código bloqueante, y no queremos
    congelar el event loop que atiende las peticiones HTTP mientras tanto.
    """
    while True:
        try:
            await asyncio.to_thread(worker.ciclo_una_vez)
        except Exception:
            logger.exception("Error en el ciclo de scraping en segundo plano")
        await asyncio.sleep(INTERVALO_POLLING_SEGUNDOS)


@app.on_event("startup")
async def _startup():
    global _tarea_worker
    db.init_db()
    _tarea_worker = asyncio.create_task(_loop_worker_en_segundo_plano())
    logger.info(
        "Worker en segundo plano iniciado (cada %d segundos).",
        INTERVALO_POLLING_SEGUNDOS,
    )


@app.on_event("shutdown")
async def _shutdown():
    if _tarea_worker:
        _tarea_worker.cancel()


@app.get("/api/parte-general")
def parte_general():
    parte = db.obtener_parte_general_mas_reciente()
    if parte is None:
        return {}
    return parte


@app.get("/api/partes")
def partes_por_provincia(
    provincia: str = Query(...),
    limite: int = Query(default=20, le=50),
):
    return db.obtener_partes_por_provincia(provincia=provincia, limite=limite)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/scrape-now")
async def scrape_now(token: str = Query(...)):
    """
    Dispara un ciclo de scraping inmediatamente. Pensado para que un cron
    externo gratuito (ej. GitHub Actions, ver DEPLOY_FREE.md) lo llame cada
    pocos minutos: esto además "despierta" el servicio si estaba dormido
    por inactividad (típico de planes free como el de Render).

    Es redundante con el loop en segundo plano de _loop_worker_en_segundo_plano
    mientras el proceso está despierto, pero eso no es un problema: guardar
    un parte ya guardado es una operación idempotente (ver mensajes_procesados
    en db.py), así que llamarlo de más nunca duplica datos.
    """
    if not SCRAPE_TOKEN or token != SCRAPE_TOKEN:
        raise HTTPException(status_code=403, detail="Token inválido o no configurado")

    await asyncio.to_thread(worker.ciclo_una_vez)
    return {"status": "ok"}
