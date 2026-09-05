# Desplegar este backend 100% GRATIS (sin tarjeta en ningún lado)

Combo usado: **Neon** (base de datos Postgres gratis) + **Render** (donde
corre el código, plan Free) + **GitHub Actions** (cron gratis que dispara
el scraping cada 10 minutos).

## Por qué estas 3 piezas y no solo una

Render (como casi toda plataforma gratis) "duerme" el servicio si nadie lo
usa por un rato, y **borra el disco local** cada vez que se duerme y
despierta. Eso significa que si guardáramos los datos en un archivo
(como SQLite), se perderían todo el tiempo. Por eso los partes se guardan
en una base de datos **externa** (Neon), que sigue viva sin importar lo
que le pase al servicio de Render.

Y como Render puede dormirse, usamos GitHub Actions (totalmente gratis,
sin límite de tiempo) para "tocar" el backend cada 10 minutos — eso lo
despierta si estaba dormido y dispara el scraping de Telegram.

## Paso 1 — Crear la base de datos en Neon (gratis, sin tarjeta)

1. Entra a https://neon.tech y crea una cuenta (puede ser con GitHub o Google).
2. Crea un proyecto nuevo (cualquier nombre, ej. "une-partes").
3. En el dashboard del proyecto, busca la **Connection String** — algo así:
   ```
   postgresql://usuario:contraseña@ep-algo-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Cópiala completa, la vas a necesitar en el Paso 3.

## Paso 2 — Subir el código a GitHub

Si el código aún no está en un repositorio:

```bash
cd backend_une
git init
git add .
git commit -m "Backend inicial"
```

Crea un repo nuevo en GitHub (puede ser privado) y sube ("push") el código.

## Paso 3 — Crear el servicio en Render (gratis, sin tarjeta)

1. Entra a https://render.com y crea una cuenta (con GitHub es lo más simple).
2. **New** → **Web Service** → conecta el repositorio de GitHub del Paso 2.
3. Configuración del servicio:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
4. En **Environment** (variables de entorno), agrega:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | la connection string de Neon (Paso 1) |
   | `SCRAPE_TOKEN` | inventa una clave larga y secreta, ej. `a8f3k2m9x7q1` |
   | `FIREBASE_CREDENTIALS_JSON` | (opcional) pegar el JSON completo de Firebase si ya lo tienes |

5. Dale a **Create Web Service**. Render construye y despliega — tarda
   unos minutos la primera vez.
6. Cuando termine, Render te da una URL tipo:
   ```
   https://une-partes-backend.onrender.com
   ```
   Guárdala, la necesitas en el Paso 4 y para configurar la app Flutter.

## Paso 4 — Configurar el cron de GitHub Actions

El repositorio ya incluye el archivo `.github/workflows/scrape-cron.yml`
que llama al backend cada 10 minutos. Solo falta darle los 2 datos que
necesita, como "Secrets" del repositorio:

1. En GitHub, entra al repositorio → **Settings** → **Secrets and
   variables** → **Actions** → **New repository secret**.
2. Crea estos dos secrets:

   | Nombre | Valor |
   |---|---|
   | `BACKEND_URL` | la URL de Render del Paso 3 (SIN barra `/` al final), ej. `https://une-partes-backend.onrender.com` |
   | `SCRAPE_TOKEN` | el mismo valor que pusiste en Render en el Paso 3 |

3. Listo — GitHub Actions ya va a correr el cron cada 10 minutos
   automáticamente. Puedes verlo funcionar en la pestaña **Actions** del
   repositorio.
4. Para probarlo ya, sin esperar 10 minutos: pestaña **Actions** →
   selecciona el workflow "Disparar scraping periódico" → **Run workflow**
   (botón manual, gracias a `workflow_dispatch` que ya está configurado).

## Paso 5 — Verificar que todo funciona

Abre en el navegador:
```
https://TU-URL-DE-RENDER.onrender.com/api/health
```
Debe responder `{"status": "ok"}` (si Render estaba dormido, puede tardar
20-40 segundos en despertar la primera vez).

Y la documentación interactiva:
```
https://TU-URL-DE-RENDER.onrender.com/docs
```

## Paso 6 — Conectar la app Flutter

En `lib/services/api_service.dart` del frontend:

```dart
static const String baseUrl = 'https://TU-URL-DE-RENDER.onrender.com/api';
```

**Aviso importante para el usuario final**: como el servicio gratis de
Render puede estar "dormido", la primera petición después de un rato de
inactividad puede tardar unos 20-40 segundos en responder. Esto ya está
cubierto en la app porque `ApiService` cae a datos mock si la petición
tarda más de 8 segundos — pero si quieres una experiencia más pulida
más adelante, se puede aumentar ese tiempo de espera o mostrar un mensaje
de "cargando, esto puede tardar un poco" la primera vez.

## Costos y límites a tener en cuenta (para que no sea sorpresa)

- **Render Free**: se duerme tras 15 min sin peticiones (nuestro cron de
  GitHub Actions cada 10 min debería mantenerlo casi siempre despierto,
  aunque no es 100% garantizado). Sin límite de tiempo total de uso.
- **Neon Free**: incluye un proyecto con almacenamiento gratuito generoso
  para este volumen de datos (miles de partes de texto ocupan muy poco).
  Revisa los límites actuales en https://neon.tech/pricing por si cambian.
- **GitHub Actions**: gratis e ilimitado para repositorios públicos;
  para repos privados hay minutos gratis mensuales de sobra para este uso
  (unas pocas ejecuciones cortas cada 10 minutos).

Ninguno de los tres pide tarjeta de crédito para el plan gratuito.

## Qué hacer si algo falla

- **Render responde 502 o no arranca**: revisar los logs en Render →
  pestaña "Logs"; casi siempre es un error de conexión a `DATABASE_URL`
  (revisar que la connection string de Neon esté completa y bien pegada).
- **El cron de GitHub Actions falla**: revisar en la pestaña "Actions" el
  log de la ejecución; frecuentemente es que `BACKEND_URL` o `SCRAPE_TOKEN`
  no coinciden exactamente con lo configurado en Render.
- **Los datos no aparecen en la app**: probar manualmente
  `https://TU-URL/api/scrape-now?token=TU_TOKEN` (método POST, se puede
  probar con la pestaña `/docs`) y revisar los logs de Render para ver
  si el scraper encontró algún error al leer Telegram.
