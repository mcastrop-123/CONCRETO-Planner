CONCRETO Planner
Sistema de programación y planificación de vaciados de concreto
CONCRETO Planner es una aplicación de escritorio desarrollada en Python para apoyar la planificación y programación de vaciados de concreto. El sistema organiza los viajes de los camiones mezcladores a partir de las condiciones operativas de la planta y la obra, considerando capacidades, tiempos de cargue, transporte, descarga y retorno.
Su propósito es facilitar la coordinación del suministro, evaluar el cumplimiento de los tiempos establecidos e identificar posibles inconvenientes durante la operación.

Objetivo
Desarrollar una herramienta que permita planificar la distribución y el suministro de concreto durante un vaciado, optimizando la organización de los recursos disponibles y proporcionando información útil para la toma de decisiones.
Funcionalidades principales
Programación de viajes: organización de los despachos de acuerdo con la disponibilidad de los camiones y los tiempos operativos.
Control de tiempos: cálculo del tiempo transcurrido desde el inicio del cargue hasta la finalización de la descarga.
Validación de mezclas: identificación de mezclas que superan el tiempo admisible establecido.
Control de volúmenes: diferenciación entre volumen atendido, desperdiciado y pendiente.
Alertas operativas: identificación de tiempos de espera e interrupciones que superan los límites configurados.
Gestión de usuarios: registro e inicio de sesión mediante Firebase Authentication.
Historial: almacenamiento y consulta de programaciones mediante Firebase Firestore.
Tecnologías utilizadas
Tecnología
Aplicación
Python
Lenguaje de programación
PySide6
Desarrollo de la interfaz gráfica
Firebase Authentication
Autenticación de usuarios
Firebase Firestore
Almacenamiento de información
Requests
Comunicación con los servicios de Firebase
PyInstaller
Generación de la aplicación ejecutable

Estructura del proyecto
CONCRETO-Planner/
│
├── interfaz.py
├── main.py
├── programacion.py
├── resultados.py
├── validaciones.py
├── requirements.txt
├── icono.icns
├── icono.png
│
├── README.md
├── Manual de usuario.pdf
├── Evidencias/
└── Registro_uso_IA.pdf
Requisitos
Python 3.
macOS para ejecutar la versión de escritorio desarrollada para esta plataforma.
Conexión a internet para las funciones de autenticación e historial.
Dependencias especificadas en requirements.txt.
Instalación y ejecución
1. Clonar el repositorio
git clone URL_DEL_REPOSITORIO
2. Acceder al proyecto
cd CONCRETO-Planner
3. Instalar las dependencias
pip3 install -r requirements.txt
4. Ejecutar la aplicación
python3 interfaz.py
Para ejecutar el módulo de programación desde la terminal:
python3 main.py
Funcionamiento general
El proceso de programación se desarrolla en las siguientes etapas:
Ingreso de las condiciones generales del vaciado.
Registro de los camiones y sus características operativas.
Validación de la información suministrada.
Cálculo y organización de los viajes.
Evaluación del tiempo admisible de cada mezcla.
Clasificación de las mezclas aceptadas y rechazadas.
Presentación de los volúmenes atendidos, desperdiciados y pendientes, junto con las alertas operativas.
Documentación
El repositorio incluye documentación complementaria para facilitar la comprensión y utilización del sistema:
Manual de usuario: describe el acceso, ingreso de información, ejecución e interpretación de resultados.
Evidencias: reúne capturas y registros de las pruebas realizadas.
Registro de uso de inteligencia artificial: documenta el apoyo de herramientas de inteligencia artificial durante el proceso de desarrollo.
Alcance
CONCRETO Planner es un proyecto académico orientado al apoyo de la planificación de vaciados de concreto. La calidad de los resultados depende de la precisión de los datos ingresados y de las condiciones operativas definidas por el usuario.
La programación generada constituye una herramienta de apoyo para la toma de decisiones y debe contrastarse con las condiciones reales de la obra.

Proyecto académico — CONCRETO Planner

