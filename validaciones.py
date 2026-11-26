
import math
import re


def validar_datos(
    volumen,
    hora_inicio,
    hora_planta,
    hora_cierre,
    camiones,
    max_espera,
    max_interrupcion,
    max_tiempo_admisible
):

    errores = []

    try:
        if not math.isfinite(float(volumen)) or float(volumen) <= 0:
            errores.append("El volumen debe ser mayor que cero y finito.")
    except (ValueError, TypeError):
        errores.append("El volumen debe ser un número válido.")

    limites = {
        "Espera máxima": max_espera,
        "Interrupción máxima": max_interrupcion,
        "Tiempo admisible": max_tiempo_admisible
    }

    for nombre, valor in limites.items():
        try:
            if not math.isfinite(float(valor)) or float(valor) <= 0:
                errores.append(
                    f"{nombre}: debes ingresar un valor mayor que cero."
                )
        except (ValueError, TypeError):
            errores.append(
                f"{nombre}: debes ingresar un valor numérico válido."
            )

    def convertir_hora(hora):
        if not isinstance(hora, str) or not re.fullmatch(r"\d{2}:\d{2}", hora):
            raise ValueError

        h, m = map(int, hora.split(":"))

        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError

        return h * 60 + m

    try:
        inicio = convertir_hora(hora_inicio)
        planta = convertir_hora(hora_planta)
        cierre = convertir_hora(hora_cierre)

        if cierre <= planta:
            errores.append(
                "El cierre debe ser posterior a la disponibilidad de planta."
            )

        if cierre <= inicio:
            errores.append(
                "El cierre debe ser posterior al inicio del vaciado."
            )

    except (ValueError, AttributeError):
        errores.append("Una o más horas tienen un formato inválido.")

    if not camiones:
        errores.append("Debe ingresar al menos un camión.")

    identificadores = []

    for camion in camiones:
        identificador = camion.get("id")

        if not identificador or not identificador.strip():
            errores.append("Hay un camión sin identificador.")
        elif identificador in identificadores:
            errores.append(f"Identificador repetido: {identificador}.")
        else:
            identificadores.append(identificador)

        try:
            capacidad = float(camion.get("capacidad", 0))
            if not math.isfinite(capacidad) or capacidad <= 0:
                raise ValueError
        except (ValueError, TypeError):
            errores.append(f"Capacidad inválida: {identificador}.")

        for tiempo in ["cargue", "viaje", "descarga", "retorno"]:
            try:
                valor = float(camion.get(tiempo))
                if not math.isfinite(valor) or valor <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                errores.append(
                    f"Tiempo inválido de {tiempo}: {identificador}."
                )

    return errores
