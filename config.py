"""
Configuración central del backend.

IMPORTANTE: completa los usernames reales de los canales de Telegram
de cada provincia (los que aparecen después de t.me/ en la URL del canal).
Puedes tener varios canales por provincia si la empresa eléctrica local
publica en más de uno.

Los valores marcados con os.environ.get(...) se pueden sobreescribir con
variables de entorno al desplegar (ej. en Railway), sin tener que tocar
este archivo ni volver a subir código.
"""

import os

# canal_username -> provincia (deben existir como keys en cuba_data del frontend)
CANALES_POR_PROVINCIA = {
    "EmpresaElectricaDeLaHabana": "La Habana",
    # "EmpresaElectricaPinarDelRio": "Pinar del Río",
    # "EmpresaElectricaArtemisa": "Artemisa",
    # "EmpresaElectricaMayabeque": "Mayabeque",
    # "EmpresaElectricaMatanzas": "Matanzas",
    # "EmpresaElectricaVillaClara": "Villa Clara",
    # "EmpresaElectricaCienfuegos": "Cienfuegos",
    # "EmpresaElectricaSanctiSpiritus": "Sancti Spíritus",
    # "EmpresaElectricaCiegoDeAvila": "Ciego de Ávila",
    # "EmpresaElectricaCamaguey": "Camagüey",
    # "EmpresaElectricaLasTunas": "Las Tunas",
    # "EmpresaElectricaHolguin": "Holguín",
    # "EmpresaElectricaGranma": "Granma",
    # "EmpresaElectricaSantiagoDeCuba": "Santiago de Cuba",
    # "EmpresaElectricaGuantanamo": "Guantánamo",
    # "EmpresaElectricaIsladeLaJuventud": "Isla de la Juventud",
}

# Canal(es) donde se publica el parte general nacional de generación/déficit.
CANALES_PARTE_NACIONAL = [
    "UNElectrica",  # AJUSTAR: username real del canal nacional
]

# Cada cuántos segundos el worker revisa los canales (ver conversación:
# 3-5 min es razonable para no saturar y mantener info fresca).
INTERVALO_POLLING_SEGUNDOS = int(os.environ.get("INTERVALO_POLLING_SEGUNDOS", "240"))

# Ruta del archivo SQLite. YA NO SE USA desde que db.py migró a Postgres
# (ver DEPLOY_FREE.md) — se deja aquí solo por compatibilidad, pero lo
# relevante ahora es la variable de entorno DATABASE_URL que lee db.py
# directamente (connection string de Postgres, ej. la que te da Neon.tech).
DB_PATH = os.environ.get("DB_PATH", "une_partes.db")

# User-Agent para las peticiones a t.me (algunos sitios bloquean requests
# sin user-agent que parezca un navegador real).
HTTP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Credenciales de Firebase Admin SDK para poder enviar push a los topics.
# Descarga el JSON desde: Firebase Console > Configuración del proyecto >
# Cuentas de servicio > Generar nueva clave privada.
#
# Dos formas de configurarlo (ver fcm.py):
#   1. Variable de entorno FIREBASE_CREDENTIALS_JSON con el contenido
#      completo del JSON pegado como texto (recomendado para Railway,
#      no requiere subir un archivo).
#   2. Un archivo en esta ruta (más simple para correr localmente).
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "FIREBASE_CREDENTIALS_PATH", "firebase-service-account.json"
)
