"""Ventana de autenticacion, registro y recuperacion de contrasena."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from interfaz.branding import (
    NOMBRE_APP,
    RUTA_FONDO_LOGIN,
    RUTA_ICONO_APP,
    RUTA_ICONO_APP_ICO,
    RUTA_LOGO_APP,
)
from servicios.servicio_autenticacion import (
    ErrorAutenticacion,
    ServicioAutenticacion,
    UsuarioSesion,
)


class _FondoLogin(QWidget):
    """Dibuja la imagen de fondo con opacidad controlada."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap(str(RUTA_FONDO_LOGIN))

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#EEF4F8"))

        if not self._pixmap.isNull():
            escalado = self._pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (self.width() - escalado.width()) // 2
            y = (self.height() - escalado.height()) // 2
            painter.setOpacity(0.44)
            painter.drawPixmap(x, y, escalado)
            painter.setOpacity(1.0)

        painter.fillRect(self.rect(), QColor(255, 255, 255, 138))
        painter.end()
        super().paintEvent(event)


class DialogoRecuperarContrasena(QDialog):
    """Permite restablecer la contrasena con usuario y empresa."""

    def __init__(
        self,
        servicio_autenticacion: ServicioAutenticacion,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._servicio_autenticacion = servicio_autenticacion
        self.setWindowTitle("Recuperar contrasena")
        self.setModal(True)
        self.setFixedWidth(420)
        self._configurar_interfaz()

    def _configurar_interfaz(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        titulo = QLabel("Recuperar contrasena")
        titulo.setObjectName("tituloLogin")
        layout.addWidget(titulo)

        descripcion = QLabel(
            "Confirme el usuario y la empresa para asignar una nueva contrasena."
        )
        descripcion.setObjectName("textoLoginSecundario")
        descripcion.setWordWrap(True)
        layout.addWidget(descripcion)

        self._campo_usuario = self._crear_campo("Usuario")
        self._campo_empresa = self._crear_campo("Empresa")
        self._campo_nueva = self._crear_campo("Nueva contrasena", contrasena=True)
        self._campo_confirmar = self._crear_campo(
            "Confirmar contrasena", contrasena=True
        )

        for campo in (
            self._campo_usuario,
            self._campo_empresa,
            self._campo_nueva,
            self._campo_confirmar,
        ):
            layout.addWidget(campo)

        acciones = QHBoxLayout()
        acciones.setSpacing(10)

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("botonSecundarioLogin")
        cancelar.clicked.connect(self.reject)

        guardar = QPushButton("Restablecer")
        guardar.setObjectName("botonPrimarioLogin")
        guardar.setDefault(True)
        guardar.clicked.connect(self._restablecer)

        acciones.addWidget(cancelar)
        acciones.addWidget(guardar)
        layout.addLayout(acciones)

    def _crear_campo(self, placeholder: str, contrasena: bool = False) -> QLineEdit:
        campo = QLineEdit()
        campo.setObjectName("campoLogin")
        campo.setPlaceholderText(placeholder)
        if contrasena:
            campo.setEchoMode(QLineEdit.Password)
        return campo

    def _restablecer(self) -> None:
        nueva = self._campo_nueva.text()
        confirmar = self._campo_confirmar.text()
        if nueva != confirmar:
            QMessageBox.warning(self, "Recuperar contrasena", "Las contrasenas no coinciden.")
            return

        try:
            self._servicio_autenticacion.restablecer_contrasena(
                usuario=self._campo_usuario.text(),
                empresa=self._campo_empresa.text(),
                nueva_contrasena=nueva,
            )
        except ErrorAutenticacion as error:
            QMessageBox.warning(self, "Recuperar contrasena", str(error))
            return

        QMessageBox.information(
            self,
            "Recuperar contrasena",
            "La contrasena se actualizo correctamente.",
        )
        self.accept()


class VentanaLogin(QDialog):
    """Login inicial de FarmaFlow con registro de usuarios locales."""

    def __init__(
        self,
        servicio_autenticacion: ServicioAutenticacion,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._servicio_autenticacion = servicio_autenticacion
        self._sesion: UsuarioSesion | None = None

        self.setWindowTitle(f"{NOMBRE_APP} - Acceso")
        if RUTA_ICONO_APP_ICO.exists():
            self.setWindowIcon(QIcon(str(RUTA_ICONO_APP_ICO)))
        self.resize(1080, 680)
        self.setMinimumSize(940, 620)
        self._configurar_interfaz()
        self._aplicar_estilos()
        self._mostrar_modo(0)

    @property
    def sesion(self) -> UsuarioSesion | None:
        """Usuario autenticado tras aceptar el dialogo."""
        return self._sesion

    def _configurar_interfaz(self) -> None:
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        fondo = _FondoLogin(self)
        fondo_layout = QHBoxLayout(fondo)
        fondo_layout.setContentsMargins(64, 52, 64, 52)
        fondo_layout.setSpacing(28)

        fondo_layout.addWidget(self._crear_bloque_marca(), stretch=1)
        fondo_layout.addWidget(self._crear_panel_formulario(), stretch=0)
        raiz.addWidget(fondo)

    def _crear_bloque_marca(self) -> QWidget:
        bloque = QWidget()
        layout = QVBoxLayout(bloque)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addStretch(1)

        logo = QLabel("FarmaFlow")
        logo.setObjectName("logoLogin")
        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if RUTA_LOGO_APP.exists():
            pixmap = QPixmap(str(RUTA_LOGO_APP))
            if not pixmap.isNull():
                logo.setText("")
                logo.setPixmap(
                    pixmap.scaled(
                        390,
                        132,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
        layout.addWidget(logo)

        titulo = QLabel("Gestion y clasificacion de movimientos")
        titulo.setObjectName("tituloHeroLogin")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        subtitulo = QLabel("Acceda a su espacio de trabajo o registre una cuenta local.")
        subtitulo.setObjectName("subtituloHeroLogin")
        subtitulo.setWordWrap(True)
        layout.addWidget(subtitulo)
        layout.addStretch(2)
        return bloque

    def _crear_panel_formulario(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panelLogin")
        panel.setFixedWidth(430)
        sombra = QGraphicsDropShadowEffect(panel)
        sombra.setBlurRadius(32)
        sombra.setOffset(0, 12)
        sombra.setColor(QColor(18, 78, 120, 42))
        panel.setGraphicsEffect(sombra)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        icono = QLabel("FF")
        icono.setObjectName("iconoLogin")
        icono.setFixedSize(52, 52)
        icono.setAlignment(Qt.AlignCenter)
        if RUTA_ICONO_APP.exists():
            pixmap = QPixmap(str(RUTA_ICONO_APP))
            if not pixmap.isNull():
                icono.setText("")
                icono.setPixmap(
                    pixmap.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        layout.addWidget(icono, alignment=Qt.AlignHCenter)

        titulo = QLabel("Acceso a FarmaFlow")
        titulo.setObjectName("tituloLogin")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)

        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self._boton_login = self._crear_boton_tab("Iniciar sesion")
        self._boton_registro = self._crear_boton_tab("Registrarse")
        self._boton_login.clicked.connect(lambda: self._mostrar_modo(0))
        self._boton_registro.clicked.connect(lambda: self._mostrar_modo(1))
        tabs.addWidget(self._boton_login)
        tabs.addWidget(self._boton_registro)
        layout.addLayout(tabs)

        self._stack_formularios = QStackedWidget()
        self._stack_formularios.addWidget(self._crear_formulario_login())
        self._stack_formularios.addWidget(self._crear_formulario_registro())
        layout.addWidget(self._stack_formularios)
        return panel

    def _crear_boton_tab(self, texto: str) -> QPushButton:
        boton = QPushButton(texto)
        boton.setObjectName("botonTabLogin")
        boton.setCheckable(True)
        return boton

    def _crear_formulario_login(self) -> QWidget:
        formulario = QWidget()
        layout = QVBoxLayout(formulario)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(12)

        self._login_usuario = self._crear_campo("Usuario")
        self._login_contrasena = self._crear_campo("Contrasena", contrasena=True)
        self._login_contrasena.returnPressed.connect(self._iniciar_sesion)

        layout.addWidget(self._login_usuario)
        layout.addWidget(self._login_contrasena)

        recuperar = QPushButton("Recuperar contrasena")
        recuperar.setObjectName("botonTextoLogin")
        recuperar.clicked.connect(self._abrir_recuperacion)
        layout.addWidget(recuperar, alignment=Qt.AlignRight)

        entrar = QPushButton("Iniciar sesion")
        entrar.setObjectName("botonPrimarioLogin")
        entrar.setDefault(True)
        entrar.clicked.connect(self._iniciar_sesion)
        layout.addWidget(entrar)
        layout.addStretch(1)
        return formulario

    def _crear_formulario_registro(self) -> QWidget:
        formulario = QWidget()
        layout = QVBoxLayout(formulario)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(10)

        self._registro_nombres = self._crear_campo("Nombres")
        self._registro_apellidos = self._crear_campo("Apellidos")
        self._registro_empresa = self._crear_campo("Empresa")
        self._registro_usuario = self._crear_campo("Usuario")
        self._registro_contrasena = self._crear_campo("Contrasena", contrasena=True)
        self._registro_confirmar = self._crear_campo(
            "Confirmar contrasena", contrasena=True
        )
        self._registro_confirmar.returnPressed.connect(self._registrar)

        for campo in (
            self._registro_nombres,
            self._registro_apellidos,
            self._registro_empresa,
            self._registro_usuario,
            self._registro_contrasena,
            self._registro_confirmar,
        ):
            layout.addWidget(campo)

        registrar = QPushButton("Registrar cuenta")
        registrar.setObjectName("botonPrimarioLogin")
        registrar.clicked.connect(self._registrar)
        layout.addWidget(registrar)
        return formulario

    def _crear_campo(self, placeholder: str, contrasena: bool = False) -> QLineEdit:
        campo = QLineEdit()
        campo.setObjectName("campoLogin")
        campo.setPlaceholderText(placeholder)
        if contrasena:
            campo.setEchoMode(QLineEdit.Password)
        return campo

    def _mostrar_modo(self, indice: int) -> None:
        self._stack_formularios.setCurrentIndex(indice)
        botones = (self._boton_login, self._boton_registro)
        for i, boton in enumerate(botones):
            activo = i == indice
            boton.setChecked(activo)
            boton.setProperty("activo", activo)
            boton.style().unpolish(boton)
            boton.style().polish(boton)

    def _iniciar_sesion(self) -> None:
        try:
            self._sesion = self._servicio_autenticacion.autenticar(
                self._login_usuario.text(),
                self._login_contrasena.text(),
            )
        except ErrorAutenticacion as error:
            QMessageBox.warning(self, "Inicio de sesion", str(error))
            return
        self.accept()

    def _registrar(self) -> None:
        contrasena = self._registro_contrasena.text()
        confirmar = self._registro_confirmar.text()
        if contrasena != confirmar:
            QMessageBox.warning(self, "Registro", "Las contrasenas no coinciden.")
            return

        try:
            self._sesion = self._servicio_autenticacion.registrar(
                usuario=self._registro_usuario.text(),
                contrasena=contrasena,
                empresa=self._registro_empresa.text(),
                nombres=self._registro_nombres.text(),
                apellidos=self._registro_apellidos.text(),
            )
        except ErrorAutenticacion as error:
            QMessageBox.warning(self, "Registro", str(error))
            return

        QMessageBox.information(self, "Registro", "Cuenta registrada correctamente.")
        self.accept()

    def _abrir_recuperacion(self) -> None:
        dialogo = DialogoRecuperarContrasena(self._servicio_autenticacion, self)
        dialogo.exec()

    def _aplicar_estilos(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #EEF4F8;
            }

            QFrame#panelLogin {
                background-color: rgba(255, 255, 255, 238);
                border: 1px solid rgba(217, 226, 236, 210);
                border-radius: 8px;
            }

            QLabel#tituloHeroLogin {
                color: #12395C;
                font-size: 30px;
                font-weight: 800;
            }

            QLabel#subtituloHeroLogin,
            QLabel#textoLoginSecundario {
                color: #52606D;
                font-size: 14px;
            }

            QLabel#tituloLogin {
                color: #12395C;
                font-size: 22px;
                font-weight: 800;
            }

            QLabel#iconoLogin {
                background-color: #FFFFFF;
                border: 1px solid #D9E2EC;
                border-radius: 8px;
                color: #124E78;
                font-weight: 800;
            }

            QLineEdit#campoLogin {
                background-color: #FFFFFF;
                border: 1px solid #D9E2EC;
                border-radius: 7px;
                color: #1F2933;
                font-size: 13px;
                min-height: 38px;
                padding: 7px 12px;
            }

            QLineEdit#campoLogin:focus {
                border-color: #124E78;
            }

            QPushButton#botonPrimarioLogin {
                background-color: #124E78;
                border: 1px solid #124E78;
                border-radius: 7px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 800;
                min-height: 40px;
                padding: 8px 14px;
            }

            QPushButton#botonPrimarioLogin:hover {
                background-color: #0B3F66;
                border-color: #0B3F66;
            }

            QPushButton#botonSecundarioLogin {
                background-color: #FFFFFF;
                border: 1px solid #D9E2EC;
                border-radius: 7px;
                color: #1F2933;
                font-weight: 800;
                min-height: 36px;
                padding: 7px 14px;
            }

            QPushButton#botonTabLogin {
                background-color: #F2F5F7;
                border: 1px solid #D9E2EC;
                border-radius: 7px;
                color: #52606D;
                font-weight: 800;
                min-height: 34px;
                padding: 7px 12px;
            }

            QPushButton#botonTabLogin[activo="true"] {
                background-color: #D8ECE4;
                border-color: #2B6C58;
                color: #1F2933;
            }

            QPushButton#botonTextoLogin {
                background-color: transparent;
                border: none;
                color: #124E78;
                font-size: 12px;
                font-weight: 800;
                padding: 2px 0px;
            }

            QPushButton#botonTextoLogin:hover {
                color: #0B3F66;
            }
            """
        )
