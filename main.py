
from programacion import programar_vaciado
from validaciones import validar_datos
from resultados import mostrar_resultados


def main():
    print("=" * 55)
    print("       PROGRAMACIÓN DE VACIADOS DE CONCRETO")
    print("=" * 55)

    try:
        volumen = float(input("\nVolumen requerido (m³): "))
        hora_inicio = input("Hora de inicio (HH:MM): ")
        hora_planta = input("Disponibilidad de planta (HH:MM): ")
        hora_cierre = input("Fin de ventana de trabajo (HH:MM): ")

        max_espera = int(input("Espera máxima permitida (min): "))
        max_interrupcion = int(
            input("Interrupción máxima permitida (min): ")
        )
        max_tiempo_admisible = int(
            input("Tiempo admisible (min): ")
        )

        if min(
            max_espera,
            max_interrupcion,
            max_tiempo_admisible
        ) <= 0:
            print("\nError: los tres límites deben ser mayores que cero.")
            return

        cantidad = int(input("\nCantidad de camiones: "))

        if cantidad <= 0:
            print("\nError: debe ingresar al menos un camión.")
            return

        camiones = []

        for i in range(cantidad):
            print(f"\n--- Datos del camión {i + 1} ---")

            camion = {
                "id": input("Identificador: ").strip(),
                "capacidad": float(input("Capacidad (m³): ")),
                "cargue": int(input("Tiempo de cargue (min): ")),
                "viaje": int(input("Tiempo de viaje (min): ")),
                "descarga": int(input("Tiempo de descarga (min): ")),
                "retorno": int(input("Tiempo de retorno (min): "))
            }

            camiones.append(camion)

        errores = validar_datos(
            volumen,
            hora_inicio,
            hora_planta,
            hora_cierre,
            camiones,
            max_espera,
            max_interrupcion,
            max_tiempo_admisible
        )

        if errores:
            print("\nERRORES EN LOS DATOS:")
            for error in errores:
                print("-", error)
            return

        resultado = programar_vaciado(
            volumen,
            hora_inicio,
            hora_planta,
            hora_cierre,
            camiones,
            max_espera,
            max_interrupcion,
            max_tiempo_admisible
        )

        mostrar_resultados(resultado)

    except ValueError:
        print("\nError: ingrese valores numéricos y horas válidas.")

    except Exception as error:
        print(f"\nError inesperado: {error}")


if __name__ == "__main__":
    main()
