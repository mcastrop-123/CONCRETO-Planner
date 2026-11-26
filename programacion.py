
def a_minutos(hora):
    horas, minutos = map(int, hora.split(":"))
    if not (0 <= horas < 24 and 0 <= minutos < 60):
        raise ValueError("Hora inválida.")
    return horas * 60 + minutos


def a_hora(minutos):
    horas = minutos // 60
    minutos_restantes = minutos % 60
    return f"{horas:02d}:{minutos_restantes:02d}"


def programar_vaciado(
    volumen_requerido,
    hora_inicio,
    disponibilidad_planta,
    fin_ventana,
    camiones,
    max_espera=None,
    max_interrupcion=None,
    max_tiempo_admisible=None
):
    inicio = a_minutos(hora_inicio)
    planta_libre = a_minutos(disponibilidad_planta)
    cierre = a_minutos(fin_ventana)

    flota = [
        {**camion, "disponible": planta_libre}
        for camion in camiones
    ]

    pendiente = volumen_requerido
    atendido = 0
    desperdiciado = 0
    bomba_libre = inicio
    ultima_descarga = None

    agenda = []
    rechazados = []
    alertas = []

    # Evita repetir indefinidamente una mezcla que siempre
    # superaría el límite con los mismos tiempos.
    camiones_con_mezcla_rechazada = set()

    while pendiente > 0:

        disponibles = [
            camion for camion in flota
            if camion["id"] not in camiones_con_mezcla_rechazada
        ]

        if not disponibles:
            break

        camion = min(
            disponibles,
            key=lambda c: (c["disponible"], str(c["id"]))
        )

        inicio_cargue = max(camion["disponible"], planta_libre)
        fin_cargue = inicio_cargue + camion["cargue"]
        salida = fin_cargue
        llegada = salida + camion["viaje"]

        inicio_descarga = max(llegada, bomba_libre)
        fin_descarga = inicio_descarga + camion["descarga"]

        if fin_descarga > cierre:
            alertas.append(
                "Se alcanzó el límite de la ventana de trabajo."
            )
            break

        retorno = fin_descarga + camion["retorno"]
        espera = inicio_descarga - llegada

        interrupcion = (
            0 if ultima_descarga is None
            else max(0, inicio_descarga - ultima_descarga)
        )

        volumen = min(camion["capacidad"], pendiente)

        tiempo_total = fin_descarga - inicio_cargue

        viaje = {
            "camion": camion["id"],
            "volumen": volumen,
            "inicio_cargue": a_hora(inicio_cargue),
            "fin_cargue": a_hora(fin_cargue),
            "salida": a_hora(salida),
            "llegada": a_hora(llegada),
            "inicio_descarga": a_hora(inicio_descarga),
            "fin_descarga": a_hora(fin_descarga),
            "retorno": a_hora(retorno),
            "disponible": a_hora(retorno),
            "espera": espera,
            "interrupcion": interrupcion,
            "tiempo_total": tiempo_total
        }

        # La mezcla se descarga físicamente, pero se rechaza
        # si el tiempo total supera el límite.
        if (
            max_tiempo_admisible is not None
            and tiempo_total > max_tiempo_admisible
        ):
            viaje["motivo"] = "Superó el tiempo admisible."

            rechazados.append({
                **viaje,
                "limite": max_tiempo_admisible
            })

            desperdiciado += volumen
            camiones_con_mezcla_rechazada.add(camion["id"])

        else:
            agenda.append(viaje)
            atendido += volumen
            pendiente -= volumen

        if max_espera is not None and espera > max_espera:
            alertas.append(
                f"Espera máxima superada por {camion['id']}."
            )

        if (
            max_interrupcion is not None
            and interrupcion > max_interrupcion
        ):
            alertas.append(
                f"Interrupción máxima superada antes de "
                f"la descarga de {camion['id']}."
            )

        # El camión regresa vacío y queda disponible nuevamente.
        camion["disponible"] = retorno

        # La planta y la bomba también se utilizaron,
        # incluso cuando la mezcla fue rechazada.
        planta_libre = fin_cargue
        bomba_libre = fin_descarga
        ultima_descarga = fin_descarga

    if pendiente > 0:
        alertas.append(
            f"Quedaron {pendiente:.2f} m³ pendientes por programar."
        )

    return {
        "agenda": agenda,
        "rechazados": rechazados,
        "volumen_atendido": atendido,
        "volumen_desperdiciado": desperdiciado,
        "volumen_pendiente": pendiente,
        "alertas": alertas
    }
