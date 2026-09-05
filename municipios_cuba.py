"""
Espejo en Python de lib/data/cuba_data.dart del frontend.
Se usa para detectar qué municipio(s) menciona un parte, comparando
el texto del mensaje contra estos nombres (sin acentos, insensible a mayúsculas).

IMPORTANTE: si actualizas la lista en Flutter, actualiza también esta,
para que el matching de municipios siga siendo consistente entre
backend y frontend.
"""

PROVINCIAS_MUNICIPIOS = {
    "Pinar del Río": [
        "Sandino", "Mantua", "Minas de Matahambre", "Viñales", "La Palma",
        "Consolación del Sur", "Pinar del Río", "San Luis", "San Juan y Martínez",
        "Guane", "Los Palacios",
    ],
    "Artemisa": [
        "Bahía Honda", "San Cristóbal", "Candelaria", "Artemisa", "Bauta",
        "Caimito", "Guanajay", "Mariel", "Güira de Melena", "Alquízar",
        "San Antonio de los Baños",
    ],
    "La Habana": [
        "Playa", "Plaza de la Revolución", "Centro Habana", "Habana Vieja",
        "Regla", "Habana del Este", "Guanabacoa", "San Miguel del Padrón",
        "Diez de Octubre", "Cerro", "Marianao", "La Lisa", "Boyeros",
        "Arroyo Naranjo", "Cotorro",
    ],
    "Mayabeque": [
        "Bejucal", "San José de las Lajas", "Jaruco", "Santa Cruz del Norte",
        "Madruga", "Nueva Paz", "San Nicolás", "Güines", "Melena del Sur",
        "Batabanó", "Quivicán",
    ],
    "Matanzas": [
        "Matanzas", "Cárdenas", "Martí", "Colón", "Perico", "Jovellanos",
        "Pedro Betancourt", "Limonar", "Unión de Reyes", "Ciénaga de Zapata",
        "Jagüey Grande", "Calimete", "Los Arabos",
    ],
    "Villa Clara": [
        "Manicaragua", "Santa Clara", "Ranchuelo", "Cifuentes", "Santo Domingo",
        "Camajuaní", "Remedios", "Placetas", "Caibarién", "Sagua la Grande",
        "Quemado de Güines", "Encrucijada", "Corralillo",
    ],
    "Cienfuegos": [
        "Aguada de Pasajeros", "Rodas", "Palmira", "Cruces", "Lajas",
        "Cienfuegos", "Cumanayagua", "Abreus",
    ],
    "Sancti Spíritus": [
        "Yaguajay", "Jatibonico", "Taguasco", "Cabaiguán", "Fomento",
        "Sancti Spíritus", "Trinidad", "La Sierpe",
    ],
    "Ciego de Ávila": [
        "Chambas", "Morón", "Bolivia", "Primero de Enero", "Ciro Redondo",
        "Florencia", "Majagua", "Ciego de Ávila", "Venezuela", "Baraguá",
    ],
    "Camagüey": [
        "Carlos Manuel de Céspedes", "Esmeralda", "Sierra de Cubitas", "Minas",
        "Nuevitas", "Guáimaro", "Sibanicú", "Camagüey", "Florida", "Vertientes",
        "Jimaguayú", "Najasa", "Santa Cruz del Sur",
    ],
    "Las Tunas": [
        "Manatí", "Puerto Padre", "Jesús Menéndez", "Majibacoa", "Las Tunas",
        "Jobabo", "Colombia", "Amancio",
    ],
    "Holguín": [
        "Gibara", "Rafael Freyre", "Banes", "Antilla", "Báguanos", "Holguín",
        "Calixto García", "Cacocum", "Urbano Noris", "Cueto", "Mayarí",
        "Frank País", "Sagua de Tánamo", "Moa",
    ],
    "Granma": [
        "Río Cauto", "Cauto Cristo", "Jiguaní", "Bayamo", "Yara", "Manzanillo",
        "Campechuela", "Media Luna", "Niquero", "Pilón", "Bartolomé Masó",
        "Buey Arriba", "Guisa",
    ],
    "Santiago de Cuba": [
        "Contramaestre", "Mella", "San Luis", "Songo-La Maya", "Santiago de Cuba",
        "Segundo Frente", "Guamá", "Palma Soriano", "Tercer Frente",
    ],
    "Guantánamo": [
        "El Salvador", "Manuel Tames", "Yateras", "Baracoa", "Maisí", "Imías",
        "San Antonio del Sur", "Guantánamo", "Caimanera", "Niceto Pérez",
    ],
    "Isla de la Juventud": ["Isla de la Juventud"],
}


def _sin_acentos(texto: str) -> str:
    reemplazos = str.maketrans("áéíóúñÁÉÍÓÚÑ", "aeiounAEIOUN")
    return texto.translate(reemplazos)


def detectar_municipios(provincia: str, texto: str) -> list[str]:
    """
    Devuelve los municipios de `provincia` que se mencionan en `texto`,
    comparando de forma insensible a mayúsculas/acentos.
    Si no detecta ninguno, devuelve lista vacía (el parte queda asociado
    solo a la provincia, sin municipio específico).
    """
    municipios = PROVINCIAS_MUNICIPIOS.get(provincia, [])
    texto_normalizado = _sin_acentos(texto).lower()

    encontrados = []
    for municipio in municipios:
        if _sin_acentos(municipio).lower() in texto_normalizado:
            encontrados.append(municipio)
    return encontrados
