import sys
import subprocess
import re
import uuid
import requests
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QLineEdit, QMessageBox, QCompleter, QListView,
    QAbstractItemView, QTimeEdit
)
from PySide6.QtCore import Qt, QStringListModel, QTime, QLocale
from PySide6.QtGui import QDoubleValidator, QIntValidator

from programacion import programar_vaciado
from validaciones import validar_datos


FIREBASE_API_KEY = "AIzaSyAefg81AfXM7AoJStUzHX1f-YTIV1oiA_A"
FIREBASE_PROJECT_ID = "concreto-planner"
USUARIO_ACTUAL = None

AUTH_URL = "https://identitytoolkit.googleapis.com/v1"
FIRESTORE_URL = (
    f"https://firestore.googleapis.com/v1/projects/"
    f"{FIREBASE_PROJECT_ID}/databases/(default)/documents"
)


# =========================================================
# FIREBASE Y AUTENTICACIÓN
# =========================================================

def _firebase_error(respuesta):
    try:
        mensaje = respuesta.json().get(
            "error", {}
        ).get("message", "Error desconocido")
    except ValueError:
        mensaje = "No fue posible comunicarse con Firebase."

    equivalencias = {
        "EMAIL_EXISTS": "Ese correo ya está registrado.",
        "INVALID_EMAIL": "El correo electrónico no es válido.",
        "WEAK_PASSWORD": "La contraseña debe tener al menos 6 caracteres.",
        "EMAIL_NOT_FOUND": "No existe una cuenta con ese correo.",
        "INVALID_PASSWORD": "La contraseña es incorrecta.",
        "INVALID_LOGIN_CREDENTIALS": "Correo o contraseña incorrectos.",
        "USER_DISABLED": "Esta cuenta fue deshabilitada.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Demasiados intentos. Inténtalo más tarde.",
        "OPERATION_NOT_ALLOWED": "Activa Email/Password en Firebase Authentication.",
    }

    codigo = mensaje.split(" : ")[0]
    return equivalencias.get(
        codigo, mensaje.replace("_", " ").capitalize()
    )


def _auth_post(accion, datos):
    respuesta = requests.post(
        f"{AUTH_URL}/{accion}?key={FIREBASE_API_KEY}",
        json=datos,
        timeout=20
    )

    if not respuesta.ok:
        raise ValueError(_firebase_error(respuesta))

    return respuesta.json()


def registrar_usuario(email, contrasena):
    cuenta = _auth_post("accounts:signUp", {
        "email": email,
        "password": contrasena,
        "returnSecureToken": True
    })

    try:
        _auth_post("accounts:sendOobCode", {
            "requestType": "VERIFY_EMAIL",
            "idToken": cuenta["idToken"]
        })
    except Exception:
        raise ValueError(
            "La cuenta se creó, pero no se pudo enviar el correo "
            "de verificación. Intenta iniciar sesión para reenviarlo."
        )


def iniciar_sesion_firebase(email, contrasena):
    cuenta = _auth_post("accounts:signInWithPassword", {
        "email": email,
        "password": contrasena,
        "returnSecureToken": True
    })

    datos = _auth_post(
        "accounts:lookup",
        {"idToken": cuenta["idToken"]}
    )

    usuario = datos["users"][0]

    if not usuario.get("emailVerified", False):
        try:
            _auth_post("accounts:sendOobCode", {
                "requestType": "VERIFY_EMAIL",
                "idToken": cuenta["idToken"]
            })
        except Exception:
            pass

        raise ValueError(
            "Debes verificar tu correo antes de ingresar. "
            "Revisa tu bandeja de entrada y correo no deseado."
        )

    return {
        "uid": cuenta["localId"],
        "email": cuenta["email"],
        "idToken": cuenta["idToken"],
        "refreshToken": cuenta.get("refreshToken", "")
    }


def restablecer_contrasena(email):
    _auth_post("accounts:sendOobCode", {
        "requestType": "PASSWORD_RESET",
        "email": email
    })


# =========================================================
# FIRESTORE
# =========================================================

def _a_firestore(valor):
    if valor is None:
        return {"nullValue": None}

    if isinstance(valor, bool):
        return {"booleanValue": valor}

    if isinstance(valor, int):
        return {"integerValue": str(valor)}

    if isinstance(valor, float):
        return {"doubleValue": valor}

    if isinstance(valor, str):
        return {"stringValue": valor}

    if isinstance(valor, list):
        return {
            "arrayValue": {
                "values": [_a_firestore(x) for x in valor]
            }
        }

    if isinstance(valor, dict):
        return {
            "mapValue": {
                "fields": {
                    str(k): _a_firestore(v)
                    for k, v in valor.items()
                }
            }
        }

    return {"stringValue": str(valor)}


def _desde_firestore(valor):
    if "stringValue" in valor:
        return valor["stringValue"]

    if "integerValue" in valor:
        return int(valor["integerValue"])

    if "doubleValue" in valor:
        return valor["doubleValue"]

    if "booleanValue" in valor:
        return valor["booleanValue"]

    if "nullValue" in valor:
        return None

    if "arrayValue" in valor:
        return [
            _desde_firestore(x)
            for x in valor["arrayValue"].get("values", [])
        ]

    if "mapValue" in valor:
        return {
            k: _desde_firestore(v)
            for k, v in valor["mapValue"].get("fields", {}).items()
        }

    return None


def _firestore_request(metodo, ruta, usuario, **kwargs):
    parametros = kwargs.pop("params", {})
    parametros.setdefault("key", FIREBASE_API_KEY)

    respuesta = requests.request(
        metodo,
        f"{FIRESTORE_URL}/{ruta}",
        params=parametros,
        headers={
            "Authorization": f"Bearer {usuario['idToken']}"
        },
        timeout=20,
        **kwargs
    )

    if not respuesta.ok:
        raise ValueError(_firebase_error(respuesta))

    return respuesta.json() if respuesta.content else {}


# =========================================================
# SONIDOS Y ELEMENTOS VISUALES
# =========================================================

def reproducir_sonido(tipo="navegacion"):
    if sys.platform == "darwin":
        sonidos = {
            "navegacion": "/System/Library/Sounds/Tink.aiff",
            "error": "/System/Library/Sounds/Basso.aiff",
        }

        ruta = sonidos.get(tipo, sonidos["navegacion"])

        try:
            subprocess.Popen(
                ["afplay", ruta],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return
        except OSError:
            pass

    QApplication.beep()


ESTILO = """
* {
    font-family: "SF Pro Display", "Helvetica Neue", sans-serif;
}

QMainWindow, QDialog {
    background-color: #FFFFFF;
}

QLabel {
    color: #202124;
    font-size: 13px;
}

QLabel#marca {
    font-size: 20px;
    font-weight: 700;
}

QLabel#titulo {
    font-size: 26px;
    font-weight: 700;
    color: #242424;
}

QLabel#subtitulo {
    color: #777777;
    font-size: 13px;
}

QLabel#titulo_tarjeta {
    font-size: 16px;
    font-weight: 650;
}

QLineEdit, QTimeEdit {
    background-color: #F1F1F2;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 9px 11px;
    color: #252525;
    font-size: 13px;
    min-height: 18px;
}

QLineEdit:focus, QTimeEdit:focus {
    background-color: white;
    border: 1px solid #777777;
}

QTimeEdit::up-button {
    subcontrol-origin: border;
    subcontrol-position: right top;
    width: 28px;
    height: 17px;
    background-color: #E9E9EB;
    border-top-right-radius: 8px;
    border-left: 1px solid #DADADD;
}

QTimeEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: right bottom;
    width: 28px;
    height: 17px;
    background-color: #E9E9EB;
    border-bottom-right-radius: 8px;
    border-left: 1px solid #DADADD;
}

QPushButton {
    border: none;
    border-radius: 9px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#boton_iniciar {
    background-color: #171717;
    color: white;
    padding: 13px 30px;
    font-size: 14px;
}

QPushButton#boton_iniciar:hover {
    background-color: #383838;
}

QPushButton#boton_primario {
    background-color: #202020;
    color: white;
}

QPushButton#boton_primario:hover {
    background-color: #414141;
}

QPushButton#boton_secundario {
    background-color: #EEEEF0;
    color: #333333;
}

QPushButton#boton_secundario:hover {
    background-color: #DCDCE0;
}

QPushButton#boton_eliminar {
    background-color: #FCECEC;
    color: #C43D3D;
}

QPushButton#boton_eliminar:hover {
    background-color: #F6DCDC;
}

QPushButton#boton_menu {
    background-color: transparent;
    color: #333333;
    text-align: left;
    padding: 10px;
}

QFrame#tarjeta {
    background-color: #F7F7F8;
    border: 1px solid #EEEEEF;
    border-radius: 13px;
}

QScrollArea {
    border: none;
    background: transparent;
}
"""


def mano(widget):
    widget.setCursor(Qt.PointingHandCursor)


def crear_tarjeta():
    tarjeta = QFrame()
    tarjeta.setObjectName("tarjeta")
    return tarjeta


def crear_etiqueta(texto, descripcion=""):
    contenedor = QWidget()
    fila = QHBoxLayout(contenedor)
    fila.setContentsMargins(0, 0, 0, 0)
    fila.setSpacing(5)

    etiqueta = QLabel(texto)
    etiqueta.setStyleSheet(
        "color: #777777; font-size: 12px; font-weight: 600;"
    )
    fila.addWidget(etiqueta)

    if descripcion:
        info = QLabel("ⓘ")
        info.setStyleSheet(
            "color: #777777; font-size: 13px; font-weight: 600;"
        )
        info.setCursor(Qt.WhatsThisCursor)
        info.setToolTip(descripcion)
        fila.addWidget(info)

    fila.addStretch()
    return contenedor


def crear_campo_numerico(decimales=0, placeholder=""):
    campo = QLineEdit()
    campo.setPlaceholderText(placeholder)
    campo.setClearButtonEnabled(True)

    locale = QLocale(QLocale.C)

    if decimales:
        validador = QDoubleValidator(0, 100000, decimales, campo)
        validador.setNotation(QDoubleValidator.StandardNotation)
        validador.setLocale(locale)
    else:
        validador = QIntValidator(0, 100000, campo)

    campo.setValidator(validador)
    mano(campo)
    return campo


def obtener_numero(campo, decimales=False):
    texto = campo.text().strip().replace(",", ".")

    if not texto:
        return 0.0 if decimales else 0

    return float(texto) if decimales else int(texto)


def crear_selector_hora():
    campo = QTimeEdit()
    campo.setDisplayFormat("HH:mm")
    campo.setTime(QTime(0, 0))
    campo.setWrapping(True)
    campo.setKeyboardTracking(False)
    campo.setAccelerated(True)
    campo.setButtonSymbols(QTimeEdit.UpDownArrows)
    campo.setToolTip(
        "Selecciona la hora usando las flechas o escribe directamente."
    )
    mano(campo)
    return campo


def mostrar_error(parent, titulo, mensaje):
    reproducir_sonido("error")
    QMessageBox.warning(parent, titulo, mensaje)


# =========================================================
# HISTORIAL EN FIREBASE
# =========================================================

def guardar_en_historial(resultado, datos):
    if not USUARIO_ACTUAL:
        raise ValueError("No hay una sesión activa.")

    registro = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "datos": datos,
        "resultado": resultado
    }

    documento_id = uuid.uuid4().hex
    campos = {
        k: _a_firestore(v)
        for k, v in registro.items()
    }

    _firestore_request(
        "POST",
        f"usuarios/{USUARIO_ACTUAL['uid']}/historial",
        USUARIO_ACTUAL,
        params={
            "documentId": documento_id,
            "key": FIREBASE_API_KEY
        },
        json={"fields": campos}
    )


def cargar_historial():
    if not USUARIO_ACTUAL:
        return []

    respuesta = _firestore_request(
        "GET",
        f"usuarios/{USUARIO_ACTUAL['uid']}/historial",
        USUARIO_ACTUAL,
        params={"pageSize": 1000}
    )

    registros = []

    for documento in respuesta.get("documents", []):
        campos = documento.get("fields", {})
        registro = {
            k: _desde_firestore(v)
            for k, v in campos.items()
        }
        registro["_document_id"] = documento["name"].rsplit("/", 1)[-1]
        registros.append(registro)

    return sorted(
        registros,
        key=lambda r: r.get("fecha", ""),
        reverse=True
    )


def borrar_historial_firebase():
    if not USUARIO_ACTUAL:
        raise ValueError("No hay una sesión activa.")

    respuesta = _firestore_request(
        "GET",
        f"usuarios/{USUARIO_ACTUAL['uid']}/historial",
        USUARIO_ACTUAL,
        params={"pageSize": 1000}
    )

    for documento in respuesta.get("documents", []):
        ruta = documento["name"].split("/documents/", 1)[-1]
        _firestore_request("DELETE", ruta, USUARIO_ACTUAL)


# =========================================================
# RESULTADOS
# =========================================================

class ResultadosDialog(QDialog):

    def __init__(self, resultado, fecha="", parent=None):
        super().__init__(parent)
        reproducir_sonido("navegacion")

        self.setWindowTitle("Resultados de programación")
        self.resize(850, 700)

        principal = QVBoxLayout(self)
        principal.setContentsMargins(28, 25, 28, 25)
        principal.setSpacing(15)

        titulo = QLabel("Resultados de programación")
        titulo.setObjectName("titulo")
        principal.addWidget(titulo)

        if fecha:
            principal.addWidget(QLabel(f"Fecha de registro: {fecha}"))

        volumen_atendido = resultado.get("volumen_atendido", 0)
        volumen_desperdiciado = resultado.get("volumen_desperdiciado", 0)
        volumen_pendiente = resultado.get("volumen_pendiente", 0)

        resumen = QLabel(
            f"Volumen atendido: {volumen_atendido} m³     "
            f"Volumen desperdiciado: {volumen_desperdiciado} m³     "
            f"Volumen pendiente: {volumen_pendiente} m³"
        )
        resumen.setWordWrap(True)
        resumen.setStyleSheet("font-size: 14px; font-weight: 600;")
        principal.addWidget(resumen)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        contenido = QWidget()
        lista = QVBoxLayout(contenido)
        lista.setSpacing(12)

        agenda = resultado.get("agenda", [])
        rechazados = resultado.get("rechazados", [])

        if agenda:
            titulo_viajes = QLabel("Viajes aceptados")
            titulo_viajes.setStyleSheet(
                "font-size: 16px; font-weight: 700;"
            )
            lista.addWidget(titulo_viajes)

        for i, viaje in enumerate(agenda):
            tarjeta = crear_tarjeta()
            layout = QVBoxLayout(tarjeta)
            layout.setContentsMargins(18, 16, 18, 16)
            layout.setSpacing(7)

            encabezado = QLabel(
                f"Viaje {i + 1} — Camión {viaje['camion']}"
            )
            encabezado.setStyleSheet(
                "font-size: 15px; font-weight: 700;"
            )
            layout.addWidget(encabezado)

            detalles = [
                f"Volumen: {viaje['volumen']} m³",
                f"Cargue: {viaje['inicio_cargue']} - {viaje['fin_cargue']}",
                f"Salida: {viaje['salida']}",
                f"Llegada: {viaje['llegada']}",
                f"Descarga: {viaje['inicio_descarga']} - {viaje['fin_descarga']}",
                f"Retorno: {viaje['retorno']}",
                f"Disponible nuevamente: {viaje['disponible']}",
                f"Espera: {viaje['espera']} minutos",
                f"Interrupción: {viaje['interrupcion']} minutos",
                f"Tiempo total: {viaje.get('tiempo_total', viaje.get('tiempo_admisible', 'No registrado'))} minutos"
            ]

            for detalle in detalles:
                layout.addWidget(QLabel(detalle))

            lista.addWidget(tarjeta)

        if rechazados:
            titulo_rechazados = QLabel("Mezclas rechazadas")
            titulo_rechazados.setStyleSheet(
                "font-size: 16px; font-weight: 700; color: #A34A24;"
            )
            lista.addWidget(titulo_rechazados)

            for i, mezcla in enumerate(rechazados):
                tarjeta = crear_tarjeta()
                layout = QVBoxLayout(tarjeta)
                layout.setContentsMargins(18, 16, 18, 16)
                layout.setSpacing(7)

                encabezado = QLabel(
                    f"Mezcla rechazada {i + 1} — Camión {mezcla.get('camion', '')}"
                )
                encabezado.setStyleSheet(
                    "font-size: 15px; font-weight: 700; color: #A34A24;"
                )
                layout.addWidget(encabezado)

                detalles = [
                    f"Volumen desperdiciado: {mezcla.get('volumen', 0)} m³",
                    f"Cargue: {mezcla.get('inicio_cargue', '')} - {mezcla.get('fin_cargue', '')}",
                    f"Salida: {mezcla.get('salida', '')}",
                    f"Llegada: {mezcla.get('llegada', '')}",
                    f"Descarga: {mezcla.get('inicio_descarga', '')} - {mezcla.get('fin_descarga', '')}",
                    f"Retorno: {mezcla.get('retorno', '')}",
                    f"Disponible nuevamente: {mezcla.get('disponible', mezcla.get('retorno', ''))}",
                    f"Espera: {mezcla.get('espera', 0)} minutos",
                    f"Interrupción: {mezcla.get('interrupcion', 0)} minutos",
                    f"Tiempo total: {mezcla.get('tiempo_total', mezcla.get('tiempo_admisible', 'No registrado'))} minutos",
                    f"Límite permitido: {mezcla.get('limite', 'No registrado')} minutos",
                    f"Motivo: {mezcla.get('motivo', 'Superó el tiempo admisible.')}"
                ]

                for detalle in detalles:
                    etiqueta = QLabel(detalle)
                    etiqueta.setWordWrap(True)
                    layout.addWidget(etiqueta)

                lista.addWidget(tarjeta)

        if not agenda and not rechazados:
            mensaje = QLabel("No se pudieron programar viajes.")
            mensaje.setStyleSheet("color: #777777; padding: 10px;")
            lista.addWidget(mensaje)

        if resultado.get("alertas"):
            titulo_alertas = QLabel("Alertas")
            titulo_alertas.setStyleSheet(
                "font-size: 16px; font-weight: 700; color: #A34A24;"
            )
            lista.addWidget(titulo_alertas)

            for alerta in resultado["alertas"]:
                etiqueta = QLabel("• " + alerta)
                etiqueta.setWordWrap(True)
                etiqueta.setStyleSheet("color: #A34A24;")
                lista.addWidget(etiqueta)
        else:
            correcto = QLabel("No se generaron alertas.")
            correcto.setStyleSheet(
                "color: #16805D; font-weight: 600;"
            )
            lista.addWidget(correcto)

        lista.addStretch()
        scroll.setWidget(contenido)
        principal.addWidget(scroll)

        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("boton_primario")
        mano(cerrar)
        cerrar.clicked.connect(self.accept)
        principal.addWidget(cerrar, alignment=Qt.AlignRight)


# =========================================================
# AUTOCOMPLETADO DEL HISTORIAL
# =========================================================

class ListaSugerencias(QListView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setStyleSheet(
            "QListView { background: white; border: 1px solid #D8D8D8; "
            "border-radius: 8px; padding: 4px; color: #222; }"
            "QListView::item { padding: 8px 10px; border-radius: 5px; }"
            "QListView::item:hover { background: #EAEAEA; color: #111; }"
            "QListView::item:selected { background: #202020; color: white; }"
        )

    def mouseMoveEvent(self, evento):
        indice = self.indexAt(evento.pos())

        if indice.isValid():
            self.setCurrentIndex(indice)
            self.selectionModel().select(
                indice,
                self.selectionModel().ClearAndSelect |
                self.selectionModel().Rows
            )

        super().mouseMoveEvent(evento)


# =========================================================
# HISTORIAL
# =========================================================

class HistorialDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        reproducir_sonido("navegacion")

        self.setWindowTitle("Historial")
        self.resize(850, 650)
        self.setMinimumSize(650, 500)

        try:
            self.historial = cargar_historial()
        except (requests.RequestException, ValueError) as error:
            self.historial = []
            mostrar_error(
                self,
                "No se pudo cargar el historial",
                str(error)
            )

        principal = QVBoxLayout(self)
        principal.setContentsMargins(28, 25, 28, 25)
        principal.setSpacing(15)

        titulo = QLabel("Historial de programaciones")
        titulo.setObjectName("titulo")
        principal.addWidget(titulo)

        descripcion = QLabel(
            "Consulta una programación anterior o úsala como base para crear una nueva."
        )
        descripcion.setObjectName("subtitulo")
        principal.addWidget(descripcion)

        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Buscar camión o fecha...")
        self.busqueda.setClearButtonEnabled(True)
        self.busqueda.returnPressed.connect(self.mostrar_registros)
        self.busqueda.textChanged.connect(self.mostrar_registros)

        sugerencias = set()

        for registro in self.historial:
            fecha = str(registro.get("fecha", ""))

            if fecha:
                sugerencias.add(fecha)
                sugerencias.add(fecha.split(" ")[0])

            for camion in registro.get("datos", {}).get("camiones", []):
                identificador = str(camion.get("id", "")).strip()
                if identificador:
                    sugerencias.add(identificador)

        self.modelo_sugerencias = QStringListModel(sorted(sugerencias))
        self.completador = QCompleter(self.modelo_sugerencias, self)
        self.completador.setCaseSensitivity(Qt.CaseInsensitive)
        self.completador.setFilterMode(Qt.MatchContains)
        self.completador.setCompletionMode(QCompleter.PopupCompletion)
        self.completador.setMaxVisibleItems(8)

        self.lista_sugerencias = ListaSugerencias()
        self.completador.setPopup(self.lista_sugerencias)
        self.busqueda.setCompleter(self.completador)
        self.completador.activated.connect(self.seleccionar_sugerencia)

        principal.addWidget(self.busqueda)

        self.contenedor = QWidget()
        self.lista = QVBoxLayout(self.contenedor)
        self.lista.setSpacing(12)
        self.lista.setContentsMargins(2, 2, 2, 2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.contenedor)
        principal.addWidget(scroll)

        botones = QHBoxLayout()

        borrar = QPushButton("Borrar historial")
        borrar.setObjectName("boton_eliminar")
        mano(borrar)
        borrar.clicked.connect(self.borrar_historial)

        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("boton_secundario")
        mano(cerrar)
        cerrar.clicked.connect(self.accept)

        botones.addWidget(borrar, alignment=Qt.AlignLeft)
        botones.addStretch()
        botones.addWidget(cerrar)
        principal.addLayout(botones)

        self.mostrar_registros()

    def seleccionar_sugerencia(self, texto):
        self.busqueda.setText(texto)
        self.busqueda.setCursorPosition(len(texto))
        self.mostrar_registros()

    def borrar_historial(self):
        if not self.historial:
            QMessageBox.information(
                self,
                "Historial vacío",
                "No hay programaciones guardadas para borrar."
            )
            return

        respuesta = QMessageBox.question(
            self,
            "Borrar historial",
            "¿Seguro que deseas borrar todas las programaciones guardadas?\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if respuesta != QMessageBox.Yes:
            return

        try:
            borrar_historial_firebase()
        except (requests.RequestException, ValueError) as error:
            mostrar_error(self, "Error al borrar", str(error))
            return

        self.historial = []
        self.busqueda.clear()
        self.modelo_sugerencias.setStringList([])
        self.mostrar_registros()

        reproducir_sonido("navegacion")

        QMessageBox.information(
            self,
            "Historial borrado",
            "Se eliminaron todas las programaciones guardadas."
        )

    def mostrar_registros(self):
        while self.lista.count():
            elemento = self.lista.takeAt(0)
            widget = elemento.widget()
            if widget:
                widget.deleteLater()

        consulta = self.busqueda.text().strip().lower()
        encontrados = 0

        for registro in self.historial:
            fecha = registro.get("fecha", "")
            datos = registro.get("datos", {})
            resultado = registro.get("resultado", {})

            identificadores = [
                str(camion.get("id", ""))
                for camion in datos.get("camiones", [])
            ]

            texto_busqueda = (
                fecha + " " + " ".join(identificadores)
            ).lower()

            if consulta and consulta not in texto_busqueda:
                continue

            tarjeta = crear_tarjeta()
            layout = QHBoxLayout(tarjeta)
            layout.setContentsMargins(16, 13, 16, 13)

            textos = QVBoxLayout()

            etiqueta_fecha = QLabel(fecha)
            etiqueta_fecha.setStyleSheet(
                "font-weight: 700; font-size: 14px;"
            )

            volumen = QLabel(
                f"Volumen solicitado: {datos.get('volumen', 0)} m³"
            )

            cantidad_viajes = QLabel(
                f"Viajes programados: {len(resultado.get('agenda', []))}"
            )

            textos.addWidget(etiqueta_fecha)
            textos.addWidget(volumen)
            textos.addWidget(cantidad_viajes)

            nueva = QPushButton("Crear nueva")
            nueva.setObjectName("boton_secundario")
            mano(nueva)
            nueva.clicked.connect(
                lambda checked=False, r=registro: self.crear_nueva_desde_historial(r)
            )

            ver = QPushButton("Ver detalles")
            ver.setObjectName("boton_primario")
            mano(ver)
            ver.clicked.connect(
                lambda checked=False, r=registro: self.ver_detalles(r)
            )

            layout.addLayout(textos)
            layout.addStretch()
            layout.addWidget(nueva)
            layout.addWidget(ver)

            self.lista.addWidget(tarjeta)
            encontrados += 1

        if encontrados == 0:
            mensaje = QLabel(
                "No se encontraron programaciones."
                if consulta else
                "Todavía no hay programaciones guardadas."
            )
            mensaje.setStyleSheet("color: #777777; padding: 15px;")
            self.lista.addWidget(mensaje)

        self.lista.addStretch()

    def crear_nueva_desde_historial(self, registro):
        formulario = Formulario(self, registro.get("datos", {}))
        formulario.exec()

        try:
            self.historial = cargar_historial()
            self.mostrar_registros()
        except (requests.RequestException, ValueError) as error:
            mostrar_error(self, "No se pudo actualizar el historial", str(error))

    def ver_detalles(self, registro):
        ventana = ResultadosDialog(
            registro["resultado"],
            registro.get("fecha", ""),
            self
        )
        ventana.exec()


# =========================================================
# FORMULARIO DE PROGRAMACIÓN
# =========================================================

class Formulario(QDialog):

    def __init__(self, parent=None, datos_iniciales=None):
        super().__init__(parent)
        reproducir_sonido("navegacion")
        self.datos_iniciales = datos_iniciales or {}

        self.setWindowTitle("Nueva programación")
        self.resize(900, 760)
        self.setMinimumSize(780, 650)

        self.campos_camiones = []

        principal = QVBoxLayout(self)
        principal.setContentsMargins(30, 25, 30, 25)
        principal.setSpacing(17)

        titulo = QLabel("Nueva programación")
        titulo.setObjectName("titulo")

        subtitulo = QLabel(
            "Configura los datos del vaciado y los camiones disponibles."
        )
        subtitulo.setObjectName("subtitulo")

        principal.addWidget(titulo)
        principal.addWidget(subtitulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        contenido = QWidget()
        contenido_layout = QVBoxLayout(contenido)
        contenido_layout.setContentsMargins(2, 2, 8, 2)
        contenido_layout.setSpacing(16)

        tarjeta = crear_tarjeta()
        general = QVBoxLayout(tarjeta)
        general.setContentsMargins(20, 20, 20, 20)
        general.setSpacing(15)

        titulo_general = QLabel("Datos generales")
        titulo_general.setObjectName("titulo_tarjeta")
        general.addWidget(titulo_general)

        cuadricula = QGridLayout()
        cuadricula.setHorizontalSpacing(20)
        cuadricula.setVerticalSpacing(12)

        self.volumen = crear_campo_numerico(
            2, "Ingresa el volumen"
        )

        self.hora_inicio = crear_selector_hora()
        self.hora_planta = crear_selector_hora()
        self.hora_cierre = crear_selector_hora()

        self.max_espera = crear_campo_numerico(
            placeholder="Minutos"
        )
        self.max_interrupcion = crear_campo_numerico(
            placeholder="Minutos"
        )
        self.max_tiempo_admisible = crear_campo_numerico(
            placeholder="Minutos"
        )

        campos = [
            (
                "Volumen requerido (m³)", self.volumen,
                "Cantidad total de concreto que se necesita colocar en la obra."
            ),
            (
                "Hora de inicio", self.hora_inicio,
                "Hora prevista para comenzar el vaciado de concreto."
            ),
            (
                "Disponibilidad de planta", self.hora_planta,
                "Hora a partir de la cual la planta puede comenzar a cargar camiones."
            ),
            (
                "Fin de ventana de trabajo", self.hora_cierre,
                "Hora límite para completar las descargas programadas."
            ),
            (
                "Espera máxima permitida (min)", self.max_espera,
                "Tiempo máximo para que se envíe una alerta debido a que un camión espera mucho en la obra antes de iniciar la descarga."
            ),
            (
                "Interrupción máxima permitida (min)", self.max_interrupcion,
                "Tiempo máximo para que se envíe una alerta debido a que la bomba se quedó sin concreto."
            ),
            (
                "Tiempo admisible (min)", self.max_tiempo_admisible,
                "Tiempo máximo que puede transcurrir desde que el agua entra en contacto con el cemento hasta que termina la descarga del concreto en obra. (segun la regulación)"
            )
        ]

        for i, (nombre, campo, descripcion) in enumerate(campos):
            fila = (i // 2) * 2
            columna = (i % 2) * 2
            cuadricula.addWidget(
                crear_etiqueta(nombre, descripcion), fila, columna
            )
            cuadricula.addWidget(campo, fila + 1, columna)

        cuadricula.setColumnStretch(1, 1)
        cuadricula.setColumnStretch(3, 1)

        general.addLayout(cuadricula)
        contenido_layout.addWidget(tarjeta)

        titulo_flota = QLabel("Flota de camiones")
        titulo_flota.setObjectName("titulo_tarjeta")
        contenido_layout.addWidget(titulo_flota)

        self.lista_camiones = QVBoxLayout()
        self.lista_camiones.setSpacing(12)
        contenido_layout.addLayout(self.lista_camiones)

        agregar = QPushButton("+ Agregar camión")
        agregar.setObjectName("boton_secundario")
        mano(agregar)
        agregar.clicked.connect(self.agregar_camion)
        contenido_layout.addWidget(agregar, alignment=Qt.AlignLeft)

        scroll.setWidget(contenido)
        principal.addWidget(scroll)

        botones = QHBoxLayout()
        botones.addStretch()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("boton_secundario")
        mano(cancelar)
        cancelar.clicked.connect(self.reject)

        guardar = QPushButton("Guardar y programar")
        guardar.setObjectName("boton_primario")
        mano(guardar)
        guardar.clicked.connect(self.guardar_datos)

        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        principal.addLayout(botones)

        self.agregar_camion()
        self.cargar_datos_iniciales()

    def cargar_datos_iniciales(self):
        datos = self.datos_iniciales
        if not datos:
            return

        self.setWindowTitle("Nueva programación basada en historial")

        self.volumen.setText(str(datos.get("volumen", "")))
        self.max_espera.setText(str(datos.get("max_espera", "")))
        self.max_interrupcion.setText(str(datos.get("max_interrupcion", "")))
        self.max_tiempo_admisible.setText(
            str(datos.get("max_tiempo_admisible", ""))
        )

        for campo, clave in (
            (self.hora_inicio, "hora_inicio"),
            (self.hora_planta, "hora_planta"),
            (self.hora_cierre, "hora_cierre"),
        ):
            hora = QTime.fromString(str(datos.get(clave, "00:00")), "HH:mm")
            if hora.isValid():
                campo.setTime(hora)

        camiones = datos.get("camiones", [])

        while len(self.campos_camiones) < len(camiones):
            self.agregar_camion()

        while len(self.campos_camiones) > max(1, len(camiones)):
            camion = self.campos_camiones[-1]
            self.eliminar_camion(camion)

        for campos, camion in zip(self.campos_camiones, camiones):
            campos["id"].setText(str(camion.get("id", "")))

            for clave in (
                "capacidad", "cargue", "viaje", "descarga", "retorno"
            ):
                campos[clave].setText(str(camion.get(clave, 0)))

    def agregar_camion(self):
        numero = len(self.campos_camiones) + 1

        tarjeta = crear_tarjeta()
        layout = QVBoxLayout(tarjeta)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        encabezado = QHBoxLayout()

        nombre = QLabel(f"Camión {numero}")
        nombre.setObjectName("titulo_tarjeta")

        eliminar = QPushButton("Eliminar")
        eliminar.setObjectName("boton_eliminar")
        mano(eliminar)

        encabezado.addWidget(nombre)
        encabezado.addStretch()
        encabezado.addWidget(eliminar)
        layout.addLayout(encabezado)

        cuadricula = QGridLayout()
        cuadricula.setHorizontalSpacing(18)
        cuadricula.setVerticalSpacing(12)

        identificador = QLineEdit()
        identificador.setPlaceholderText("Ej. C1")

        capacidad = crear_campo_numerico(
            2, "Capacidad en m³"
        )
        cargue = crear_campo_numerico(
            placeholder="Minutos"
        )
        viaje = crear_campo_numerico(
            placeholder="Minutos"
        )
        descarga = crear_campo_numerico(
            placeholder="Minutos"
        )
        retorno = crear_campo_numerico(
            placeholder="Minutos"
        )

        campos = [
            (
                "Identificador", identificador,
                "Nombre o código único para identificar el camión, por ejemplo C1."
            ),
            (
                "Capacidad (m³)", capacidad,
                "Cantidad máxima de concreto que puede transportar el camión en un viaje."
            ),
            (
                "Tiempo de cargue (min)", cargue,
                "Duración del proceso de carga del concreto en la planta, en minutos."
            ),
            (
                "Tiempo de viaje (min)", viaje,
                "Tiempo que tarda el camión desde la salida de la planta hasta la obra."
            ),
            (
                "Tiempo de descarga (min)", descarga,
                "Duración de la descarga del concreto en la obra."
            ),
            (
                "Tiempo de retorno (min)", retorno,
                "Tiempo que tarda el camión en regresar desde la obra hasta la planta."
            )
        ]

        for i, (nombre_campo, campo, descripcion) in enumerate(campos):
            fila = (i // 2) * 2
            columna = (i % 2) * 2
            cuadricula.addWidget(
                crear_etiqueta(nombre_campo, descripcion), fila, columna
            )
            cuadricula.addWidget(campo, fila + 1, columna)

        cuadricula.setColumnStretch(1, 1)
        cuadricula.setColumnStretch(3, 1)

        layout.addLayout(cuadricula)

        datos = {
            "tarjeta": tarjeta,
            "nombre": nombre,
            "id": identificador,
            "capacidad": capacidad,
            "cargue": cargue,
            "viaje": viaje,
            "descarga": descarga,
            "retorno": retorno
        }

        self.campos_camiones.append(datos)
        self.lista_camiones.addWidget(tarjeta)

        eliminar.clicked.connect(
            lambda checked=False, d=datos: self.eliminar_camion(d)
        )

    def eliminar_camion(self, datos):
        if len(self.campos_camiones) <= 1:
            mostrar_error(
                self,
                "Aviso",
                "Debe existir al menos un camión."
            )
            return

        self.campos_camiones.remove(datos)
        datos["tarjeta"].deleteLater()

        for i, camion in enumerate(self.campos_camiones):
            camion["nombre"].setText(f"Camión {i + 1}")

    def guardar_datos(self):
        volumen = obtener_numero(self.volumen, True)

        hora_inicio = self.hora_inicio.time().toString("HH:mm")
        hora_planta = self.hora_planta.time().toString("HH:mm")
        hora_cierre = self.hora_cierre.time().toString("HH:mm")

        camiones = []

        for camion in self.campos_camiones:
            camiones.append({
                "id": camion["id"].text().strip(),
                "capacidad": obtener_numero(
                    camion["capacidad"], True
                ),
                "cargue": obtener_numero(camion["cargue"]),
                "viaje": obtener_numero(camion["viaje"]),
                "descarga": obtener_numero(camion["descarga"]),
                "retorno": obtener_numero(camion["retorno"])
            })

        max_espera = obtener_numero(self.max_espera)
        max_interrupcion = obtener_numero(self.max_interrupcion)
        max_tiempo_admisible = obtener_numero(
            self.max_tiempo_admisible
        )

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
            mostrar_error(
                self,
                "Errores en los datos",
                "\n".join("• " + error for error in errores)
            )
            return

        try:
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
        except (ValueError, KeyError, TypeError) as error:
            mostrar_error(
                self,
                "Error de programación",
                str(error)
            )
            return

        datos = {
            "volumen": volumen,
            "hora_inicio": hora_inicio,
            "hora_planta": hora_planta,
            "hora_cierre": hora_cierre,
            "max_espera": max_espera,
            "max_interrupcion": max_interrupcion,
            "max_tiempo_admisible": max_tiempo_admisible,
            "camiones": camiones
        }

        try:
            guardar_en_historial(resultado, datos)
        except (OSError, requests.RequestException, ValueError) as error:
            mostrar_error(
                self,
                "Error al guardar",
                f"No se pudo guardar el historial: {error}"
            )
            return

        self.accept()

        ventana = ResultadosDialog(resultado, parent=self.parent())
        ventana.exec()


# =========================================================
# REGISTRO DE CUENTA
# =========================================================

class RegistroDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Crear cuenta")
        self.setFixedSize(430, 390)
        reproducir_sonido("navegacion")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(12)

        titulo = QLabel("Crear cuenta")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        texto = QLabel(
            "Regístrate con tu correo electrónico. Te enviaremos un enlace "
            "para verificar tu cuenta antes de iniciar sesión."
        )
        texto.setWordWrap(True)
        texto.setObjectName("subtitulo")
        layout.addWidget(texto)

        layout.addWidget(crear_etiqueta("Correo electrónico"))

        self.email = QLineEdit()
        self.email.setPlaceholderText("nombre@correo.com")
        layout.addWidget(self.email)

        layout.addWidget(crear_etiqueta("Contraseña"))

        self.clave = QLineEdit()
        self.clave.setEchoMode(QLineEdit.Password)
        self.clave.setPlaceholderText("Mínimo 6 caracteres")
        layout.addWidget(self.clave)

        layout.addWidget(crear_etiqueta("Confirmar contraseña"))

        self.confirmar = QLineEdit()
        self.confirmar.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirmar)

        boton = QPushButton("Crear cuenta")
        boton.setObjectName("boton_primario")
        mano(boton)
        boton.clicked.connect(self.guardar)
        layout.addWidget(boton)

    def guardar(self):
        email = self.email.text().strip()
        clave = self.clave.text()

        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            mostrar_error(
                self,
                "Correo inválido",
                "Ingresa un correo electrónico válido."
            )
            return

        if len(clave) < 6:
            mostrar_error(
                self,
                "Contraseña inválida",
                "Usa al menos 6 caracteres."
            )
            return

        if clave != self.confirmar.text():
            mostrar_error(
                self,
                "No coinciden",
                "Las contraseñas no coinciden."
            )
            return

        try:
            registrar_usuario(email, clave)
        except (requests.RequestException, ValueError) as error:
            mostrar_error(
                self,
                "No se pudo crear la cuenta",
                str(error)
            )
            return

        reproducir_sonido("navegacion")

        QMessageBox.information(
            self,
            "Verifica tu correo",
            "La cuenta fue creada. Abre el enlace que enviamos a tu correo "
            "y después inicia sesión."
        )

        self.accept()


# =========================================================
# INICIO DE SESIÓN
# =========================================================

class LoginDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.usuario = None
        self.setWindowTitle("Acceso · CONCRETO Planner")
        self.setFixedSize(440, 450)
        reproducir_sonido("navegacion")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(13)

        marca = QLabel("CONCRETO Planner")
        marca.setObjectName("marca")
        marca.setAlignment(Qt.AlignCenter)
        layout.addWidget(marca)

        titulo = QLabel("Iniciar sesión")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)

        layout.addWidget(crear_etiqueta("Correo electrónico"))

        self.email = QLineEdit()
        self.email.setPlaceholderText("nombre@correo.com")
        layout.addWidget(self.email)

        layout.addWidget(crear_etiqueta("Contraseña"))

        self.clave = QLineEdit()
        self.clave.setEchoMode(QLineEdit.Password)
        self.clave.setPlaceholderText("Tu contraseña")
        self.clave.returnPressed.connect(self.iniciar)
        layout.addWidget(self.clave)

        self.email.returnPressed.connect(self.clave.setFocus)

        entrar = QPushButton("Iniciar sesión")
        entrar.setObjectName("boton_iniciar")
        mano(entrar)
        entrar.clicked.connect(self.iniciar)
        layout.addWidget(entrar)

        registro = QPushButton("Crear cuenta")
        registro.setObjectName("boton_secundario")
        mano(registro)
        registro.clicked.connect(self.abrir_registro)
        layout.addWidget(registro)

        recuperar = QPushButton("¿Olvidaste tu contraseña?")
        recuperar.setObjectName("boton_menu")
        mano(recuperar)
        recuperar.clicked.connect(self.recuperar_contrasena)
        layout.addWidget(recuperar)

        self.email.setFocus()

    def abrir_registro(self):
        RegistroDialog(self).exec()

    def recuperar_contrasena(self):
        email = self.email.text().strip()

        if not email:
            mostrar_error(
                self,
                "Correo requerido",
                "Escribe tu correo electrónico en el campo superior."
            )
            return

        try:
            restablecer_contrasena(email)
        except (requests.RequestException, ValueError) as error:
            mostrar_error(
                self,
                "No se pudo enviar el correo",
                str(error)
            )
            return

        QMessageBox.information(
            self,
            "Revisa tu correo",
            "Enviamos un enlace para restablecer tu contraseña."
        )

    def iniciar(self):
        email = self.email.text().strip()
        clave = self.clave.text()

        if not email or not clave:
            mostrar_error(
                self,
                "Datos incompletos",
                "Escribe tu correo electrónico y contraseña."
            )
            return

        try:
            self.usuario = iniciar_sesion_firebase(email, clave)
        except (requests.RequestException, ValueError) as error:
            mostrar_error(
                self,
                "No se pudo iniciar sesión",
                str(error)
            )
            return

        self.accept()


# =========================================================
# VENTANA DE TRABAJO
# =========================================================

class VentanaTrabajo(QMainWindow):

    def __init__(self, ventana_principal):
        super().__init__()

        self.ventana_principal = ventana_principal

        self.setWindowTitle("CONCRETO Planner · Espacio de trabajo")
        self.resize(950, 650)
        self.setMinimumSize(750, 550)

        central = QWidget()
        self.setCentralWidget(central)

        principal = QVBoxLayout(central)
        principal.setContentsMargins(60, 45, 60, 45)
        principal.setSpacing(18)

        marca = QLabel("CONCRETO Planner")
        marca.setObjectName("marca")
        marca.setAlignment(Qt.AlignCenter)
        principal.addWidget(marca)

        titulo = QLabel("Espacio de trabajo")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)
        principal.addWidget(titulo)

        descripcion = QLabel(
            "Selecciona la función que deseas utilizar."
        )
        descripcion.setObjectName("subtitulo")
        descripcion.setAlignment(Qt.AlignCenter)
        principal.addWidget(descripcion)

        principal.addSpacing(30)

        programar = QPushButton("Nueva programación")
        programar.setObjectName("boton_iniciar")
        programar.setFixedSize(300, 55)
        mano(programar)
        programar.clicked.connect(self.abrir_formulario)

        historial = QPushButton("Historial")
        historial.setObjectName("boton_secundario")
        historial.setFixedSize(300, 50)
        mano(historial)
        historial.clicked.connect(self.abrir_historial)

        cerrar = QPushButton("Cerrar sesión")
        cerrar.setObjectName("boton_secundario")
        cerrar.setFixedSize(300, 45)
        mano(cerrar)
        cerrar.clicked.connect(self.cerrar_sesion)

        principal.addWidget(programar, alignment=Qt.AlignCenter)
        principal.addWidget(historial, alignment=Qt.AlignCenter)
        principal.addWidget(cerrar, alignment=Qt.AlignCenter)

        principal.addStretch()

        self.usuario_label = QLabel(
            f"Sesión activa: {USUARIO_ACTUAL.get('email', '')}"
        )
        self.usuario_label.setAlignment(Qt.AlignCenter)
        self.usuario_label.setStyleSheet(
            "color: #777777; font-size: 11px;"
        )
        principal.addWidget(self.usuario_label)

    def abrir_formulario(self):
        reproducir_sonido("navegacion")
        formulario = Formulario(self)
        formulario.exec()

    def abrir_historial(self):
        reproducir_sonido("navegacion")
        historial = HistorialDialog(self)
        historial.exec()

    def cerrar_sesion(self):
        self.ventana_principal.cerrar_sesion()
        self.close()


# =========================================================
# PRIMERA VENTANA
# =========================================================

class VentanaPrincipal(QMainWindow):

    def __init__(self):
        super().__init__()

        self.usuario = None
        self.ventana_trabajo = None

        self.setWindowTitle("CONCRETO Planner")
        self.setFixedSize(650, 520)

        central = QWidget()
        self.setCentralWidget(central)

        principal = QVBoxLayout(central)
        principal.setContentsMargins(60, 45, 60, 45)
        principal.setSpacing(16)

        principal.addStretch(2)

        marca = QLabel("CONCRETO Planner")
        marca.setObjectName("marca")
        marca.setAlignment(Qt.AlignCenter)
        principal.addWidget(marca)

        titulo = QLabel("Programación de vaciados")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)
        principal.addWidget(titulo)

        descripcion = QLabel(
            "Organiza el suministro de concreto y coordina "
            "los viajes de los camiones."
        )
        descripcion.setObjectName("subtitulo")
        descripcion.setAlignment(Qt.AlignCenter)
        descripcion.setWordWrap(True)
        principal.addWidget(descripcion)

        principal.addSpacing(35)

        self.boton_login = QPushButton("Iniciar sesión")
        self.boton_login.setObjectName("boton_iniciar")
        self.boton_login.setFixedSize(280, 52)
        mano(self.boton_login)
        self.boton_login.clicked.connect(self.iniciar_sesion)

        self.boton_cerrar = QPushButton("Cerrar sesión")
        self.boton_cerrar.setObjectName("boton_secundario")
        self.boton_cerrar.setFixedSize(280, 48)
        mano(self.boton_cerrar)
        self.boton_cerrar.clicked.connect(self.cerrar_sesion)

        principal.addWidget(
            self.boton_login,
            alignment=Qt.AlignCenter
        )
        principal.addWidget(
            self.boton_cerrar,
            alignment=Qt.AlignCenter
        )

        principal.addStretch(3)

        pie = QLabel("Proyecto de programación · Grupo 4")
        pie.setAlignment(Qt.AlignCenter)
        pie.setStyleSheet("color: #999999; font-size: 11px;")
        principal.addWidget(pie)

        self.actualizar_estado()

    def actualizar_estado(self):
        if self.usuario:
            self.boton_login.setText("Abrir espacio de trabajo")
            self.boton_cerrar.setEnabled(True)
            self.boton_cerrar.show()
        else:
            self.boton_login.setText("Iniciar sesión")
            self.boton_cerrar.hide()

    def iniciar_sesion(self):
        global USUARIO_ACTUAL

        reproducir_sonido("navegacion")

        if self.usuario:
            self.abrir_espacio_trabajo()
            return

        acceso = LoginDialog(self)

        if acceso.exec() != QDialog.Accepted:
            return

        self.usuario = acceso.usuario
        USUARIO_ACTUAL = acceso.usuario

        self.actualizar_estado()
        self.abrir_espacio_trabajo()

    def abrir_espacio_trabajo(self):
        if not self.usuario:
            return

        if self.ventana_trabajo is None:
            self.ventana_trabajo = VentanaTrabajo(self)

        self.ventana_trabajo.show()
        self.ventana_trabajo.raise_()
        self.ventana_trabajo.activateWindow()

    def cerrar_sesion(self):
        global USUARIO_ACTUAL

        if not self.usuario:
            QMessageBox.information(
                self,
                "Sin sesión",
                "No hay ninguna sesión activa."
            )
            return

        respuesta = QMessageBox.question(
            self,
            "Cerrar sesión",
            "¿Deseas cerrar tu sesión?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if respuesta != QMessageBox.Yes:
            return

        USUARIO_ACTUAL = None
        self.usuario = None

        if self.ventana_trabajo is not None:
            self.ventana_trabajo.close()
            self.ventana_trabajo = None

        self.actualizar_estado()
        reproducir_sonido("navegacion")

        QMessageBox.information(
            self,
            "Sesión cerrada",
            "Has cerrado sesión correctamente."
        )


# =========================================================
# EJECUCIÓN
# =========================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO)

    ventana = VentanaPrincipal()
    ventana.show()

    sys.exit(app.exec())