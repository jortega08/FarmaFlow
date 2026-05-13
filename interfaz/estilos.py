"""Estilos base de la interfaz."""


def obtener_estilos_base() -> str:
    """Retorna la hoja de estilos principal de la aplicacion."""
    return """
    QWidget {
        background-color: transparent;
        color: #1F2933;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 13px;
    }

    QMainWindow {
        background-color: #F2F5F7;
    }

    /* Dialogos: forzar tema claro consistente (QMessageBox, QInputDialog, QFileDialog, QDialog).
       Sin esto, en Windows con tema oscuro heredan el fondo oscuro del sistema. */
    QDialog, QMessageBox, QInputDialog, QFileDialog {
        background-color: #FFFFFF;
        color: #1F2933;
    }

    QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel, QFileDialog QLabel {
        background-color: transparent;
        color: #1F2933;
        font-size: 13px;
    }

    QMessageBox {
        background-color: #FFFFFF;
    }

    QMessageBox QLabel#qt_msgbox_label {
        color: #1F2933;
        font-size: 13px;
        min-width: 280px;
        padding: 4px 0px;
    }

    QMessageBox QLabel#qt_msgbox_informativelabel {
        color: #52606D;
        font-size: 12px;
    }

    QMessageBox QPushButton, QInputDialog QPushButton, QFileDialog QPushButton, QDialog QPushButton {
        background-color: #FFFFFF;
        color: #1F2933;
        border: 1px solid #D9E2EC;
        border-radius: 7px;
        padding: 7px 16px;
        font-weight: 700;
        min-width: 80px;
        min-height: 22px;
    }

    QMessageBox QPushButton:hover, QInputDialog QPushButton:hover,
    QFileDialog QPushButton:hover, QDialog QPushButton:hover {
        background-color: #F2F5F7;
        border-color: #D9E2EC;
    }

    QMessageBox QPushButton:default, QInputDialog QPushButton:default,
    QFileDialog QPushButton:default, QDialog QPushButton:default {
        background-color: #124E78;
        color: #FFFFFF;
        border: 1px solid #124E78;
    }

    QMessageBox QPushButton:default:hover, QInputDialog QPushButton:default:hover,
    QFileDialog QPushButton:default:hover, QDialog QPushButton:default:hover {
        background-color: #0B3F66;
        border: 1px solid #0B3F66;
    }

    QInputDialog QLineEdit, QDialog QLineEdit {
        background-color: #FFFFFF;
        color: #1F2933;
        border: 1px solid #D9E2EC;
        border-radius: 7px;
        padding: 6px 12px;
        min-height: 28px;
    }

    QFileDialog QListView, QFileDialog QTreeView {
        background-color: #FFFFFF;
        color: #1F2933;
        border: 1px solid #D9E2EC;
    }

    QFileDialog QComboBox, QFileDialog QLineEdit {
        background-color: #FFFFFF;
        color: #1F2933;
        border: 1px solid #D9E2EC;
        border-radius: 6px;
        padding: 4px 8px;
    }

    QLabel {
        background-color: transparent;
    }

    QFrame#panelArchivo,
    QFrame#panelValidacion,
    QFrame#panelPreclasificacion,
    QFrame#barraEstado,
    QFrame#barraInferior {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QFrame#barraResultadoExito {
        background-color: #D8ECE4;
        border: 1px solid #D8ECE4;
        border-radius: 8px;
    }

    QFrame#barraResultadoError {
        background-color: #F2F5F7;
        border: 1px solid #B42318;
        border-radius: 8px;
    }

    QFrame#panelOperativo {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QFrame#encabezado {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QFrame#subbloquePanel {
        background-color: #F2F5F7;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QFrame#tarjetaMetrica {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QFrame#tarjetaMetrica:hover,
    QFrame#panelArchivo:hover {
        border-color: #D9E2EC;
    }

    QStatusBar {
        background-color: transparent;
        border: none;
    }

    QStatusBar::item {
        border: none;
    }

    QLabel#tituloAplicacion {
        font-size: 26px;
        font-weight: 700;
        color: #1F2933;
    }

    QLabel#subtituloAplicacion {
        font-size: 13px;
        color: #52606D;
    }

    QLabel#tituloSeccion {
        font-size: 18px;
        font-weight: 700;
        color: #124E78;
    }

    QLabel#tituloSubpanel {
        font-size: 14px;
        font-weight: 700;
        color: #1F2933;
    }

    QLabel#textoSecundario {
        color: #52606D;
        font-size: 13px;
    }

    QLabel#tituloBloque {
        color: #52606D;
        font-size: 11px;
        font-weight: 700;
    }

    QLabel#valorCampo {
        color: #1F2933;
        font-size: 13px;
        font-weight: 700;
    }

    QLabel#valorRutaArchivo,
    QLabel#detalleObservacion {
        background-color: transparent;
        color: #1F2933;
        border: none;
        padding: 0px;
        font-size: 13px;
    }

    QLabel#descripcionPlaceholder {
        color: #52606D;
        font-size: 13px;
    }

    QLabel#etiquetaMetrica {
        color: #1F2933;
        font-size: 13px;
        font-weight: 700;
    }

    QLabel#descripcionMetrica {
        color: #52606D;
        font-size: 12px;
    }

    QLabel#valorMetrica {
        color: #124E78;
        font-size: 27px;
        font-weight: 800;
    }

    QLabel#valorMetricaCorrecto {
        color: #2B6C58;
        font-size: 27px;
        font-weight: 800;
    }

    QLabel#valorMetricaAdvertencia {
        color: #D97706;
        font-size: 27px;
        font-weight: 800;
    }

    QLabel#valorMetricaEstadoCorrecto {
        color: #2B6C58;
        font-size: 22px;
        font-weight: 800;
    }

    QLabel#valorMetricaEstadoAdvertencia {
        color: #D97706;
        font-size: 22px;
        font-weight: 800;
    }

    QLabel#pasoFlujo {
        background-color: transparent;
        color: #52606D;
        border: none;
        padding: 0px;
        font-weight: 600;
    }

    QLabel#separadorFlujo {
        color: #52606D;
        font-weight: 600;
    }

    QLabel#mensajeBarraEstado {
        color: #52606D;
    }

    QLabel#mensajeCargaInfo {
        background-color: transparent;
        color: #124E78;
        border: none;
        padding: 0px;
        font-size: 13px;
        font-weight: 600;
    }

    QLabel#mensajeCargaExito {
        background-color: transparent;
        color: #2B6C58;
        border: none;
        padding: 0px;
        font-size: 13px;
        font-weight: 600;
    }

    QLabel#mensajeCargaAdvertencia {
        background-color: transparent;
        color: #D97706;
        border: none;
        padding: 0px;
        font-size: 13px;
        font-weight: 600;
    }

    QLabel#mensajeCargaError {
        background-color: transparent;
        color: #B42318;
        border: none;
        padding: 0px;
        font-size: 13px;
        font-weight: 600;
    }

    QLabel#insigniaNeutra,
    QLabel#insigniaInfo,
    QLabel#insigniaCorrecta,
    QLabel#insigniaAdvertencia,
    QLabel#insigniaError {
        border-radius: 16px;
        padding: 5px 8px;
        font-weight: 800;
        font-size: 11px;
    }

    QLabel#insigniaNeutra {
        background-color: #F2F5F7;
        color: #52606D;
        border: 1px solid #D9E2EC;
    }

    QLabel#insigniaInfo {
        background-color: #F2F5F7;
        color: #124E78;
        border: 1px solid #D9E2EC;
    }

    QLabel#insigniaCorrecta {
        background-color: #D8ECE4;
        color: #2B6C58;
        border: 1px solid #D8ECE4;
    }

    QLabel#insigniaAdvertencia {
        background-color: #F2F5F7;
        color: #D97706;
        border: 1px solid #D97706;
    }

    QLabel#insigniaError {
        background-color: #F2F5F7;
        color: #B42318;
        border: 1px solid #B42318;
    }

    QTableWidget QLabel#insigniaNeutra,
    QTableWidget QLabel#insigniaInfo,
    QTableWidget QLabel#insigniaCorrecta,
    QTableWidget QLabel#insigniaAdvertencia,
    QTableWidget QLabel#insigniaError {
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 10px;
        font-weight: 800;
        min-height: 18px;
    }

    QLabel#contadorListaNeutro,
    QLabel#contadorListaCorrecto,
    QLabel#contadorListaAdvertencia,
    QLabel#contadorListaError,
    QLabel#contadorListaInfo {
        border-radius: 10px;
        padding: 4px 8px;
        font-weight: 700;
        min-width: 22px;
    }

    QLabel#contadorListaNeutro {
        background-color: #F2F5F7;
        color: #52606D;
    }

    QLabel#contadorListaCorrecto {
        background-color: #D8ECE4;
        color: #2B6C58;
    }

    QLabel#contadorListaAdvertencia {
        background-color: #F2F5F7;
        color: #D97706;
    }

    QLabel#contadorListaError {
        background-color: #F2F5F7;
        color: #B42318;
    }

    QLabel#contadorListaInfo {
        background-color: #D9E2EC;
        color: #124E78;
    }

    QFrame#indicadorEstadoNeutro,
    QFrame#indicadorEstadoInfo,
    QFrame#indicadorEstadoCorrecto,
    QFrame#indicadorEstadoAdvertencia,
    QFrame#indicadorEstadoError {
        border-radius: 5px;
        border: none;
    }

    QFrame#indicadorEstadoNeutro {
        background-color: #52606D;
    }

    QFrame#indicadorEstadoInfo {
        background-color: #124E78;
    }

    QFrame#indicadorEstadoCorrecto {
        background-color: #2B6C58;
    }

    QFrame#indicadorEstadoAdvertencia {
        background-color: #D97706;
    }

    QFrame#indicadorEstadoError {
        background-color: #B42318;
    }

    QPushButton {
        border-radius: 7px;
        padding: 10px 16px;
        font-weight: 700;
        min-height: 22px;
        font-size: 13px;
    }

    QPushButton#botonPrincipal {
        background-color: #124E78;
        color: #FFFFFF;
        border: 1px solid #124E78;
        font-weight: 800;
    }

    QPushButton#botonPrincipal:hover {
        background-color: #0B3F66;
        border: 1px solid #0B3F66;
    }

    QPushButton#botonPrincipal:pressed {
        background-color: #083556;
        border: 1px solid #083556;
    }

    QPushButton#botonSecundario {
        background-color: #F8FAFC;
        color: #124E78;
        border: 1px solid #C9D6E2;
        font-weight: 700;
    }

    QPushButton#botonSecundario:hover {
        background-color: #EEF3F7;
        border-color: #9FB3C8;
    }

    QPushButton#botonExito {
        background-color: #E7F4EE;
        color: #23624F;
        border: 1px solid #8FC4AD;
        font-weight: 800;
    }

    QPushButton#botonExito:hover {
        background-color: #D8ECE4;
        border: 1px solid #6FAF93;
    }

    QPushButton#botonExito:pressed {
        background-color: #C5E1D5;
        border: 1px solid #5B9E84;
    }

    QPushButton#botonPeligro {
        background-color: #FFF5F3;
        color: #B42318;
        border: 1px solid #E7AAA4;
        font-weight: 800;
    }

    QPushButton#botonPeligro:hover {
        background-color: #FDE4E1;
        border: 1px solid #D47B72;
    }

    QPushButton#botonPeligro:pressed {
        background-color: #F9CAC5;
        border: 1px solid #B42318;
    }

    QPushButton#botonTerciario {
        background-color: #F2F5F7;
        color: #52606D;
        border: 1px solid #D9E2EC;
    }

    QPushButton#botonTerciario:hover {
        background-color: #D9E2EC;
    }

    QPushButton#botonFiltroTabla {
        background-color: #F8FAFC;
        color: #124E78;
        border: 1px solid #C9D6E2;
        font-weight: 800;
    }

    QPushButton#botonFiltroTabla:hover {
        background-color: #EEF3F7;
        border-color: #9FB3C8;
    }

    QPushButton#botonFiltroTabla:checked {
        background-color: #124E78;
        color: #FFFFFF;
        border-color: #124E78;
    }

    QPushButton#botonTabla {
        background-color: #FFFFFF;
        color: #124E78;
        border: 1px solid #D9E2EC;
        border-radius: 6px;
        padding: 3px 6px;
        min-height: 20px;
        font-size: 10px;
        font-weight: 700;
    }

    QPushButton#botonTabla:hover {
        background-color: #F2F5F7;
        border-color: #124E78;
    }

    QPushButton#botonTablaPeligro {
        background-color: #FFF5F3;
        color: #B42318;
        border: 1px solid #E7AAA4;
        border-radius: 6px;
        padding: 3px 6px;
        min-height: 20px;
        font-size: 10px;
        font-weight: 800;
    }

    QPushButton#botonTablaPeligro:hover {
        background-color: #FDE4E1;
        border-color: #B42318;
    }

    QPushButton:disabled {
        background-color: #D9E2EC;
        color: #52606D;
        border: 1px solid #D9E2EC;
    }

    QListWidget {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
        padding: 8px;
        outline: none;
    }

    QListWidget::item {
        padding: 8px 4px;
        border-bottom: 1px solid #D9E2EC;
    }

    QListWidget::item:selected {
        background-color: #D9E2EC;
        color: #1F2933;
    }

    QFrame#sidebar {
        background-color: #FFFFFF;
        border-right: 1px solid #D9E2EC;
        border-radius: 0px;
    }

    QFrame#sidebarHeader {
        background-color: transparent;
        border-bottom: 1px solid #D9E2EC;
        border-radius: 0px;
    }

    QLabel#appNameSidebar {
        color: #124E78;
        font-size: 13px;
        font-weight: 800;
        background-color: transparent;
    }

    QLabel#logoSidebar {
        color: #124E78;
        font-size: 25px;
        font-weight: 800;
        background-color: transparent;
        border: none;
    }

    QLabel#iconoSidebar {
        background-color: #F2F5F7;
        color: #124E78;
        border: 2px solid #2B6C58;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 900;
    }

    QLabel#seccionNavTitle {
        color: #52606D;
        font-size: 10px;
        font-weight: 800;
        background-color: transparent;
    }

    QFrame#itemNavNormal {
        background-color: transparent;
        border-radius: 8px;
        border: none;
    }

    QFrame#itemNavNormal:hover {
        background-color: #F2F5F7;
    }

    QFrame#itemNavActivo {
        background-color: #F2F5F7;
        border-radius: 8px;
        border: 1px solid #D9E2EC;
    }

    QLabel#textoNavNormal {
        color: #52606D;
        font-size: 13px;
        font-weight: 500;
        background-color: transparent;
    }

    QLabel#textoNavActivo {
        color: #124E78;
        font-size: 13px;
        font-weight: 800;
        background-color: transparent;
    }

    QLabel#badgeNumNav {
        background-color: #D9E2EC;
        color: #52606D;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 800;
        min-width: 24px;
        min-height: 24px;
    }

    QLabel#badgeNumNavActivo {
        background-color: #124E78;
        color: #FFFFFF;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 800;
        min-width: 24px;
        min-height: 24px;
    }

    QLabel#badgeNumNavCompletado {
        background-color: #2B6C58;
        color: #FFFFFF;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 800;
        min-width: 24px;
        min-height: 24px;
    }

    QFrame#separadorSidebar {
        background-color: #D9E2EC;
        border: none;
        border-radius: 0px;
    }

    QFrame#sidebarFooter {
        background-color: transparent;
        border-top: 1px solid #D9E2EC;
        border-radius: 0px;
    }

    QLabel#versionSidebar {
        color: #52606D;
        font-size: 11px;
        background-color: transparent;
    }

    QFrame#headerGlobal {
        background-color: #FFFFFF;
        border-bottom: 1px solid #D9E2EC;
        border-radius: 0px;
    }

    QFrame#footerNavegacion {
        background-color: #FFFFFF;
        border-top: 1px solid #D9E2EC;
        border-radius: 0px;
    }

    QLabel#subtituloNav {
        color: #52606D;
        font-size: 11px;
        font-weight: 500;
        background-color: transparent;
    }

    QLabel#subtituloNavActivo {
        color: #124E78;
        font-size: 11px;
        font-weight: 600;
        background-color: transparent;
    }

    QFrame#panelGuiaReglas {
        background-color: #F2F5F7;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QLabel#badgePasoGuia {
        background-color: #124E78;
        color: #FFFFFF;
        border-radius: 14px;
        font-size: 13px;
        font-weight: 800;
        min-width: 28px;
        min-height: 28px;
    }

    QLabel#appTitleGlobal {
        font-size: 25px;
        font-weight: 800;
        color: #1F2933;
        background-color: transparent;
    }

    QLabel#appSubtitleGlobal {
        font-size: 13px;
        color: #52606D;
        background-color: transparent;
    }

    QLabel#iconoHeader {
        background-color: transparent;
        color: #124E78;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 900;
    }

    QFrame#panelDerecho {
        background-color: #F2F5F7;
        border: none;
        border-radius: 0px;
    }

    QWidget#contenedorVista {
        background-color: #F2F5F7;
    }

    QScrollArea {
        background-color: transparent;
        border: none;
    }

    QFrame#uploadZone {
        background-color: #FFFFFF;
        border: 1px dashed #D9E2EC;
        border-radius: 8px;
    }

    QFrame#uploadZone:hover {
        border-color: #124E78;
        background-color: #F2F5F7;
    }

    QLabel#iconoExcel {
        color: #FFFFFF;
        background-color: #2B6C58;
        border-radius: 8px;
        font-size: 17px;
        font-weight: 900;
    }

    QLabel#tituloUpload {
        color: #1F2933;
        font-size: 13px;
        font-weight: 700;
    }

    QLabel#textoFormatos {
        color: #52606D;
        font-size: 11px;
        background-color: transparent;
    }

    QFrame#infoArchivo {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QFrame#infoArchivoActivo {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
    }

    QLabel#iconoDocumento {
        color: #FFFFFF;
        background-color: #52606D;
        border-radius: 6px;
        font-size: 10px;
        font-weight: 900;
    }

    QLabel#nombreArchivo {
        color: #1F2933;
        font-size: 14px;
        font-weight: 800;
        background-color: transparent;
    }

    QLabel#metadatoArchivo {
        color: #1F2933;
        font-size: 12px;
        background-color: transparent;
    }

    QLabel#iconoTarjetaInfo,
    QLabel#iconoTarjetaExito,
    QLabel#iconoTarjetaNeutro,
    QLabel#iconoTarjetaAdvertencia {
        border-radius: 8px;
        font-size: 12px;
        font-weight: 900;
    }

    QLabel#iconoTarjetaInfo {
        background-color: #F2F5F7;
        color: #124E78;
    }

    QLabel#iconoTarjetaExito {
        background-color: #D8ECE4;
        color: #2B6C58;
    }

    QLabel#iconoTarjetaNeutro {
        background-color: #F2F5F7;
        color: #52606D;
    }

    QLabel#iconoTarjetaAdvertencia {
        background-color: #F2F5F7;
        color: #D97706;
    }

    QFrame#itemResumenVal {
        background-color: transparent;
        border: none;
        border-radius: 0px;
    }

    QFrame#divisorVertical {
        background-color: #D9E2EC;
        border: none;
        border-radius: 0px;
        min-width: 1px;
        max-width: 1px;
    }

    QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 8px;
        gridline-color: #D9E2EC;
        selection-background-color: #D9E2EC;
        selection-color: #1F2933;
        alternate-background-color: #F2F5F7;
    }

    QTableWidget::item {
        padding: 6px 8px;
        border: none;
    }

    QHeaderView::section {
        background-color: #F2F5F7;
        color: #1F2933;
        font-weight: 800;
        font-size: 11px;
        padding: 8px 6px;
        border: none;
        border-bottom: 1px solid #D9E2EC;
        border-right: 1px solid #D9E2EC;
    }

    QHeaderView {
        background-color: #F2F5F7;
    }

    QProgressBar {
        background-color: #D9E2EC;
        border: none;
        border-radius: 5px;
        min-height: 10px;
        max-height: 10px;
        text-align: center;
        color: transparent;
    }

    QProgressBar::chunk {
        background-color: #2B6C58;
        border-radius: 5px;
    }

    QLabel#iconoEstadoNeutro,
    QLabel#iconoEstadoInfo,
    QLabel#iconoEstadoCorrecto,
    QLabel#iconoEstadoAdvertencia,
    QLabel#iconoEstadoError {
        border-radius: 15px;
        font-size: 10px;
        font-weight: 900;
        min-width: 30px;
        min-height: 30px;
    }

    QLabel#iconoEstadoNeutro {
        background-color: #F2F5F7;
        color: #52606D;
        border: 1px solid #D9E2EC;
    }

    QLabel#iconoEstadoInfo {
        background-color: #F2F5F7;
        color: #124E78;
        border: 1px solid #D9E2EC;
    }

    QLabel#iconoEstadoCorrecto {
        background-color: #D8ECE4;
        color: #2B6C58;
        border: 1px solid #D8ECE4;
    }

    QLabel#iconoEstadoAdvertencia {
        background-color: #F2F5F7;
        color: #D97706;
        border: 1px solid #D97706;
    }

    QLabel#iconoEstadoError {
        background-color: #F2F5F7;
        color: #B42318;
        border: 1px solid #B42318;
    }

    QLabel#mensajeEstado {
        color: #2B6C58;
        font-size: 13px;
        font-weight: 700;
        background-color: transparent;
    }

    QLabel#mensajeEstadoError {
        color: #B42318;
        font-size: 13px;
        font-weight: 700;
        background-color: transparent;
    }

    QLabel#mensajeEstadoAdvertencia {
        color: #D97706;
        font-size: 13px;
        font-weight: 700;
        background-color: transparent;
    }

    QLabel#mensajeEstadoNeutro {
        color: #52606D;
        font-size: 13px;
        font-weight: 700;
        background-color: transparent;
    }

    QLineEdit, QSpinBox {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 7px;
        padding: 6px 12px;
        color: #1F2933;
        font-size: 13px;
        min-height: 36px;
    }

    QLineEdit:focus, QSpinBox:focus {
        border-color: #124E78;
    }

    QComboBox {
        background-color: #F8FAFC;
        border: 1px solid #C9D6E2;
        border-radius: 7px;
        padding: 6px 34px 6px 12px;
        color: #1F2933;
        font-size: 13px;
        min-height: 36px;
    }

    QComboBox:focus {
        border-color: #124E78;
    }

    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 22px;
        border-left: 1px solid #D9E2EC;
        background-color: #EEF3F7;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
    }

    QComboBox::down-arrow {
        image: none;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #52606D;
        margin-right: 6px;
    }

    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 6px;
        selection-background-color: #D9E2EC;
    }

    QCheckBox {
        color: #1F2933;
        font-weight: 700;
        spacing: 8px;
        background-color: transparent;
    }

    QCheckBox::indicator {
        width: 34px;
        height: 18px;
        border-radius: 9px;
        background-color: #D9E2EC;
        border: 1px solid #D9E2EC;
    }

    QCheckBox::indicator:checked {
        background-color: #2B6C58;
        border: 1px solid #2B6C58;
    }

    QCheckBox#checkSalida::indicator {
        width: 16px;
        height: 16px;
        border-radius: 4px;
        background-color: #FFFFFF;
        border: 1px solid #D9E2EC;
    }

    QCheckBox#checkSalida::indicator:checked {
        background-color: #2B6C58;
        border: 1px solid #2B6C58;
    }
    """
