# Backend — Partes Eléctricos Cuba

Scraper + parser + API para consolidar los partes eléctricos de Telegram.

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

1. Edita `config.py`:
   - `CANALES_POR_PROVINCIA`: agrega el username real de cada canal de
     Telegram (lo que va después de `t.me/`, ej. `EmpresaElectricaDeLaHabana`).
   - `CANALES_PARTE_NACIONAL`: el/los canal(es) donde se publica el parte
     general de generación/déficit.
   - `INTERVALO_POLLING_SEGUNDOS`: cada cuánto revisa los canales (240s = 4 min
     por defecto).

2. **Base de datos (obligatorio)**: este backend usa Postgres, no SQLite.
   Necesitas una variable de entorno `DATABASE_URL` con la connection
   string (ver `DEPLOY_FREE.md` para cómo conseguir una gratis en Neon.tech).
   Ejemplo local (con Postgres instalado en tu máquina):
   ```bash
   export DATABASE_URL="postgresql://usuario:contraseña@localhost:5432/une_partes"
   ```

3. (Opcional, necesario para push reales) Firebase — dos formas:
   - Variable de entorno `FIREBASE_CREDENTIALS_JSON` con el contenido
     completo del JSON pegado como texto (recomendado para hosting en la nube).
   - Un archivo `firebase-service-account.json` en esta carpeta (para correr
     localmente).
   - Sin ninguna de las dos, el worker funciona igual, solo que las
     notificaciones quedan en modo "no-op" (se loguean pero no se envían).

## Probar el parser (sin necesitar red)

```bash
python3 test_parser.py
```

Debe imprimir "✅ Todas las pruebas pasaron." — esto valida la lógica de
extracción contra mensajes de ejemplo con el formato real observado en
`t.me/EmpresaElectricaDeLaHabana`.

## Probar el scraper contra un canal real

```bash
python3 scraper.py EmpresaElectricaDeLaHabana
```

Imprime los últimos 5 mensajes del canal. Si esto falla, revisa que tengas
salida a internet hacia `t.me` (no se ejecuta contra un sandbox restringido).

## Correr todo junto (recomendado — API + worker en un solo proceso)

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Esto levanta la API y, en segundo plano dentro del mismo proceso, corre
el scraping de Telegram cada `INTERVALO_POLLING_SEGUNDOS`. Es el modo
pensado para desplegar en Render/Railway como un solo servicio (ver
`DEPLOY_FREE.md` para la guía paso a paso de despliegue 100% gratis).

Endpoints:
- `GET /api/parte-general` → el parte nacional más reciente.
- `GET /api/partes?provincia=La%20Habana&municipio=Playa` → partes de esa zona.
- `GET /api/health` → chequeo simple.

Documentación interactiva automática en `http://localhost:8000/docs`.

## Correr el worker por separado (opcional, solo si prefieres 2 procesos)

Si despliegas en un VPS propio y prefieres separar el scraping de la API
en dos procesos independientes (por ejemplo con systemd o Docker Compose),
puedes correr:

```bash
python3 worker.py
```

Este script hace exactamente lo mismo que la tarea en segundo plano de
`api.py`, pero como proceso aparte. Si usas este modo, asegúrate de que
ambos procesos apunten al MISMO archivo de base de datos (mismo `DB_PATH`),
o el worker guardará datos que la API nunca verá.

## Conectar con la app Flutter

En `lib/services/api_service.dart` del frontend, cambia:

```dart
static const String baseUrl = 'https://TU_BACKEND_AQUI.example.com/api';
```

Por la URL real donde despliegues esta API (mientras desarrollas localmente
y pruebas en el teléfono, puede ser la IP de tu computadora en la red local,
ej. `http://192.168.1.50:8000/api`, siempre que el teléfono esté en la
misma red Wi-Fi).

## Qué falta / siguientes pasos

- [ ] Completar `CANALES_POR_PROVINCIA` con los canales reales de cada
      provincia (solo está confirmado el de La Habana).
- [ ] Verificar que el scraper siga funcionando contra `t.me/s/...` en
      producción (la estructura HTML de Telegram podría cambiar con el tiempo).
- [ ] Revisar y ajustar los regex de `parser.py` con más ejemplos reales
      a medida que aparezcan formatos distintos (mantenimiento continuo,
      como se discutió: esto no es algo que "se termina").
- [ ] Desplegar el worker y la API en un servidor real (VPS, Cloud Run,
      Railway, etc.) con HTTPS, en vez de correrlo en tu máquina local.
- [ ] Agregar autenticación básica a la API si la expones públicamente,
      para evitar abuso.
- [ ] Considerar mover de SQLite a Postgres si el volumen de datos/usuarios
      crece mucho (la capa `db.py` está aislada justo para que esto sea
      un cambio localizado).

## Estructura

```
config.py            - canales, intervalos, rutas de configuración
scraper.py            - lee t.me/s/<canal> sin autenticación
parser.py              - clasifica y extrae campos de cada mensaje
municipios_cuba.py      - detecta qué municipio(s) menciona un mensaje
db.py                    - capa de acceso a SQLite
fcm.py                    - envío de push a topics de Firebase
worker.py                  - loop que une todo lo anterior
api.py                      - API REST (FastAPI) que consume el frontend
test_parser.py                - pruebas del parser con mensajes de ejemplo
```
