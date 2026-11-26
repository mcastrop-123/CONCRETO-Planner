
def mostrar_resultados(resultado):

    print("\n" + "=" * 65)
    print("       PROGRAMACIÓN DE VACIADOS DE CONCRETO")
    print("=" * 65)

    if resultado["agenda"]:
        print("\nMEZCLAS ACEPTADAS:")

        for viaje in resultado["agenda"]:

            print(f"\nCamión: {viaje['camion']}")
            print(f"Volumen: {viaje['volumen']} m³")
            print(
                f"Cargue: {viaje['inicio_cargue']} - "
                f"{viaje['fin_cargue']}"
            )
            print(f"Salida: {viaje['salida']}")
            print(f"Llegada: {viaje['llegada']}")
            print(
                f"Descarga: {viaje['inicio_descarga']} - "
                f"{viaje['fin_descarga']}"
            )
            print(f"Retorno: {viaje['retorno']}")
            print(f"Disponible nuevamente: {viaje['disponible']}")
            print(f"Espera: {viaje['espera']} minutos")
            print(f"Interrupción: {viaje['interrupcion']} minutos")
            print(f"Tiempo total: {viaje['tiempo_total']} minutos")

            print("-" * 65)

    if resultado["rechazados"]:
        print("\nMEZCLAS RECHAZADAS:")

        for mezcla in resultado["rechazados"]:

            print(f"\nCamión: {mezcla['camion']}")
            print(f"Volumen desperdiciado: {mezcla['volumen']} m³")
            print(
                f"Cargue: {mezcla['inicio_cargue']} - "
                f"{mezcla['fin_cargue']}"
            )
            print(f"Salida: {mezcla['salida']}")
            print(f"Llegada: {mezcla['llegada']}")
            print(
                f"Descarga: {mezcla['inicio_descarga']} - "
                f"{mezcla['fin_descarga']}"
            )
            print(f"Retorno: {mezcla['retorno']}")
            print(f"Tiempo total: {mezcla['tiempo_total']} minutos")
            print(f"Límite permitido: {mezcla['limite']} minutos")
            print(f"Motivo: {mezcla['motivo']}")

            print("-" * 65)

    print(f"\nVolumen atendido: {resultado['volumen_atendido']:.2f} m³")
    print(
        f"Volumen desperdiciado: "
        f"{resultado['volumen_desperdiciado']:.2f} m³"
    )
    print(f"Volumen pendiente: {resultado['volumen_pendiente']:.2f} m³")

    if resultado["alertas"]:
        print("\nALERTAS:")
        for alerta in resultado["alertas"]:
            print(f"- {alerta}")
    else:
        print("\nNo se generaron alertas.")

    print("=" * 65)
