from parser import parse_mensaje, TIPO_CORTE, TIPO_RESTABLECIMIENTO, TIPO_GENERAL_NACIONAL

EJEMPLO_CORTE = """⚠️⚡️Informamos a los clientes de los municipios Playa y Marianao pertenecientes a la SUBESTACIÓN de Tallapiedra, que por trabajos de mantenimiento se afectará el servicio eléctrico.
🛑Circuitos afectados:
👉D631: Calle 23 entre Paseo y G, Vedado
👉A1008: Reparto Kohly y alrededores
👉PG940: Zona del Náutico"""

EJEMPLO_RESTABLECIMIENTO = """📣✅Informamos a la población que a partir de las 3:45 PM quedó restablecido el servicio en los siguientes circuitos:
👉D631: Calle 23 entre Paseo y G, Vedado
👉A1008: Reparto Kohly y alrededores"""

EJEMPLO_GENERAL = """Parte eléctrico nacional: disponibilidad 2450 MW, demanda 2980 MW, déficit estimado 530 MW en el horario pico de la noche. Se mantienen afectaciones programadas."""

EJEMPLO_RARO = """Aviso: mañana habrá mantenimiento preventivo en varias zonas, más detalles próximamente."""


def probar(nombre, texto):
    print("=" * 70)
    print(nombre)
    print("-" * 70)
    resultado = parse_mensaje(texto)
    print("tipo:", resultado.tipo)
    print("subestacion:", resultado.subestacion)
    print("municipios_texto:", resultado.municipios_texto)
    print("hora_restablecimiento:", resultado.hora_restablecimiento)
    print("circuitos:", resultado.circuitos)
    print("deficit_mw:", resultado.deficit_mw)
    print("disponibilidad_mw:", resultado.disponibilidad_mw)
    print("demanda_mw:", resultado.demanda_mw)
    return resultado


if __name__ == "__main__":
    r1 = probar("CORTE", EJEMPLO_CORTE)
    assert r1.tipo == TIPO_CORTE
    assert r1.subestacion and "Tallapiedra" in r1.subestacion
    assert len(r1.circuitos) == 3
    assert r1.circuitos[0].codigo == "D631"

    r2 = probar("RESTABLECIMIENTO", EJEMPLO_RESTABLECIMIENTO)
    assert r2.tipo == TIPO_RESTABLECIMIENTO
    assert r2.hora_restablecimiento == "3:45 PM"
    assert len(r2.circuitos) == 2

    r3 = probar("GENERAL NACIONAL", EJEMPLO_GENERAL)
    assert r3.tipo == TIPO_GENERAL_NACIONAL
    assert r3.deficit_mw == 530
    assert r3.disponibilidad_mw == 2450
    assert r3.demanda_mw == 2980

    r4 = probar("SIN CLASIFICAR", EJEMPLO_RARO)
    assert r4.tipo == "sin_clasificar"

    print("\n✅ Todas las pruebas pasaron.")
