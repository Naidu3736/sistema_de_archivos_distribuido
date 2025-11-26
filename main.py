import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QListWidget, QTextEdit,
                            QLabel, QProgressBar, QFileDialog, QMessageBox,
                            QTabWidget, QGroupBox, QLineEdit, QSplitter,
                            QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                            QInputDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from client.file_client import FileClient
from core.logger import logger

class ConnectionDialog(QDialog):
    """Diálogo para configurar la conexión al servidor"""
    def __init__(self, current_host="localhost", current_port=8001, parent=None):
        super().__init__(parent)
        self.host = current_host
        self.port = current_port
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Configurar Conexión")
        self.setGeometry(300, 300, 400, 200)
        
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("Configuración del Servidor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #cccccc;
                padding: 10px;
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 2px;
            }
        """)
        layout.addWidget(title)
        
        # Campo para host
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Host:"))
        self.host_input = QLineEdit(self.host)
        self.host_input.setPlaceholderText("localhost")
        host_layout.addWidget(self.host_input)
        layout.addLayout(host_layout)
        
        # Campo para puerto
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit(str(self.port))
        self.port_input.setPlaceholderText("8001")
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        btn_connect = QPushButton("Conectar")
        btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #2a4a2a;
                color: #e0e0e0;
                border: 1px solid #3a5a3a;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a5a3a;
            }
        """)
        btn_connect.clicked.connect(self.accept_connection)
        buttons_layout.addWidget(btn_connect)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #4a2a2a;
                color: #e0e0e0;
                border: 1px solid #5a3a3a;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a3a3a;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        layout.addLayout(buttons_layout)
        
        # Aplicar estilos
        self.setStyleSheet("""
            QDialog {
                background-color: #2a2a2a;
            }
            QLabel {
                color: #cccccc;
            }
            QLineEdit {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 6px;
            }
        """)
    
    def accept_connection(self):
        """Acepta la conexión y valida los datos"""
        host = self.host_input.text().strip()
        port_text = self.port_input.text().strip()
        
        if not host:
            QMessageBox.warning(self, "Error", "Por favor ingrese un host válido")
            return
            
        try:
            port = int(port_text)
            if port < 1 or port > 65535:
                raise ValueError("Puerto fuera de rango")
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor ingrese un puerto válido (1-65535)")
            return
        
        self.host = host
        self.port = port
        self.accept()

class FileInfoDialog(QDialog):
    """Diálogo para mostrar información detallada del archivo"""
    def __init__(self, file_info, parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("File Information")
        self.setGeometry(200, 200, 500, 400)
        
        layout = QVBoxLayout(self)
        
        # Información del archivo
        info_text = f"""
        <h3>File Information</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">Name:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['filename']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">Size:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['size'] / (1024 * 1024):.2f} MB</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">Blocks:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['block_count']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">First Block:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['first_block_id']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">Block Chain:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['block_chain']}</td>
            </tr>
        </table>
        """
        
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        self.info_display.setHtml(info_text)
        self.info_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #cccccc;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 12px;
                font-size: 12px;
                selection-background-color: #505080;
            }
        """)
        layout.addWidget(self.info_display)
        
        # Botón de cerrar
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

class FileManagerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = None
        self.host = "localhost"
        self.port = 8001
        self.current_files_data = []
        self.init_ui()
        self.setup_logger_connection()
        # No inicializamos el cliente automáticamente
        self.update_buttons_state(False)
        # Actualizar la etiqueta del servidor con los valores por defecto
        self.update_server_label()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("File System Manager - No conectado")
        self.setGeometry(100, 100, 1200, 700)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(1)
        
        # Panel izquierdo - Estado del sistema
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Panel derecho - Contenido principal
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)
        
        # Aplicar estilo
        self.apply_dark_styles()
    
    def setup_logger_connection(self):
        """Conecta el logger al área de logs de la interfaz"""
        logger.set_ui_callback(self.add_log_to_ui)
    
    def add_log_to_ui(self, log_entry):
        """Agrega un mensaje del logger al área de logs de la UI"""
        self.log_area.addItem(log_entry)
        # Auto-scroll al final
        self.log_area.scrollToBottom()
    
    def initialize_client(self):
        """Inicializa el cliente con los parámetros de conexión actuales"""
        try:
            if self.client:
                self.client.close()
                
            self.client = FileClient(self.host, self.port)
            self.connect_to_server()
        except Exception as e:
            logger.log("GUI", f"Error inicializando cliente: {str(e)}")
            self.connection_status.setText("Error de Inicio")
    
    def create_left_panel(self):
        """Crea el panel izquierdo con el estado del sistema"""
        panel = QWidget()
        panel.setMaximumWidth(300)
        panel.setMinimumWidth(280)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(8)
        
        # Título
        title = QLabel("Estado del Sistema")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #cccccc;
                padding: 12px 5px;
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 2px;
                letter-spacing: 1px;
            }
        """)
        layout.addWidget(title)
        
        # Estado de conexión
        connection_group = QGroupBox("Conexión")
        connection_layout = QVBoxLayout(connection_group)
        
        connection_info_layout = QHBoxLayout()
        connection_info_layout.addWidget(QLabel("Servidor:"))
        self.server_label = QLabel("No configurado")  # Inicializar con texto por defecto
        self.server_label.setStyleSheet("font-weight: bold; color: #888888;")
        connection_info_layout.addWidget(self.server_label)
        connection_layout.addLayout(connection_info_layout)
        
        connection_status_layout = QHBoxLayout()
        connection_status_layout.addWidget(QLabel("Estado:"))
        self.connection_status = QLabel("SIN CONEXIÓN")
        self.connection_status.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                border-radius: 2px;
                background-color: #3a2a2a;
                color: #ff6666;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #553333;
            }
        """)
        connection_status_layout.addWidget(self.connection_status)
        connection_layout.addLayout(connection_status_layout)
        
        # Botones de conexión
        connection_buttons_layout = QHBoxLayout()
        
        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #2a4a2a;
                color: #e0e0e0;
                border: 1px solid #3a5a3a;
                padding: 6px 8px;
                border-radius: 2px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #3a5a3a;
            }
        """)
        self.btn_connect.clicked.connect(self.show_connection_dialog)
        connection_buttons_layout.addWidget(self.btn_connect)
        
        self.btn_reconnect = QPushButton("Reconectar")
        self.btn_reconnect.setStyleSheet("""
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 6px 8px;
                border-radius: 2px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        self.btn_reconnect.clicked.connect(self.reconnect_to_server)
        connection_buttons_layout.addWidget(self.btn_reconnect)
        
        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.setStyleSheet("""
            QPushButton {
                background-color: #4a2a2a;
                color: #e0e0e0;
                border: 1px solid #5a3a3a;
                padding: 6px 8px;
                border-radius: 2px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #5a3a3a;
            }
        """)
        self.btn_disconnect.clicked.connect(self.disconnect_from_server)
        connection_buttons_layout.addWidget(self.btn_disconnect)
        
        connection_layout.addLayout(connection_buttons_layout)
        layout.addWidget(connection_group)
        
        # Estadísticas del sistema
        stats_group = QGroupBox("Estadísticas del Sistema")
        stats_layout = QVBoxLayout(stats_group)
        
        # Total de archivos
        files_layout = QHBoxLayout()
        files_layout.addWidget(QLabel("Archivos Totales:"))
        self.total_files_label = QLabel("0")
        self.total_files_label.setStyleSheet("font-weight: bold; color: #88cc88;")
        files_layout.addWidget(self.total_files_label)
        stats_layout.addLayout(files_layout)
        
        # Bloques
        blocks_layout = QHBoxLayout()
        blocks_layout.addWidget(QLabel("Bloques Totales:"))
        self.total_blocks_label = QLabel("0")
        blocks_layout.addWidget(self.total_blocks_label)
        stats_layout.addLayout(blocks_layout)
        
        used_blocks_layout = QHBoxLayout()
        used_blocks_layout.addWidget(QLabel("Bloques Usados:"))
        self.used_blocks_label = QLabel("0")
        used_blocks_layout.addWidget(self.used_blocks_label)
        stats_layout.addLayout(used_blocks_layout)
        
        free_blocks_layout = QHBoxLayout()
        free_blocks_layout.addWidget(QLabel("Bloques Libres:"))
        self.free_blocks_label = QLabel("0")
        free_blocks_layout.addWidget(self.free_blocks_label)
        stats_layout.addLayout(free_blocks_layout)
        
        # Uso
        usage_layout = QHBoxLayout()
        usage_layout.addWidget(QLabel("Uso:"))
        self.usage_label = QLabel("0%")
        self.usage_label.setStyleSheet("font-weight: bold;")
        usage_layout.addWidget(self.usage_label)
        stats_layout.addLayout(usage_layout)
        
        # Espacio usado
        space_layout = QHBoxLayout()
        space_layout.addWidget(QLabel("Espacio Usado:"))
        self.used_space_label = QLabel("0 MB")
        space_layout.addWidget(self.used_space_label)
        stats_layout.addLayout(space_layout)
        
        layout.addWidget(stats_group)
        
        # Botón para actualizar estado
        self.btn_refresh_status = QPushButton("Refrescar Estado")
        self.btn_refresh_status.setStyleSheet("""
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 10px 8px;
                border-radius: 3px;
                font-size: 12px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        self.btn_refresh_status.clicked.connect(self.update_system_status)
        layout.addWidget(self.btn_refresh_status)
        
        layout.addStretch()
        return panel
    
    def create_right_panel(self):
        """Crea el panel derecho con el contenido principal"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        
        # Barra de acciones superiores
        actions_panel = self.create_actions_panel()
        layout.addWidget(actions_panel)
        
        # Lista de archivos
        files_panel = self.create_files_panel()
        layout.addWidget(files_panel)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 2px;
                text-align: center;
                background-color: #2a2a2a;
                color: #cccccc;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #505080;
                border-radius: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Área de logs
        log_panel = self.create_log_panel()
        layout.addWidget(log_panel)
        
        return panel
    
    def create_actions_panel(self):
        """Crea la barra de acciones superiores"""
        panel = QWidget()
        panel.setMaximumHeight(60)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Botones de acciones
        btn_style = """
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 8px 12px;
                border-radius: 3px;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #404040;
                border: 1px solid #505050;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #353535;
            }
        """
        
        self.btn_upload = QPushButton("Subir Archivo")
        self.btn_upload.setStyleSheet(btn_style)
        self.btn_upload.clicked.connect(self.upload_file)
        layout.addWidget(self.btn_upload)
        
        self.btn_download = QPushButton("Descargar Archivo")
        self.btn_download.setStyleSheet(btn_style)
        self.btn_download.clicked.connect(self.download_file)
        layout.addWidget(self.btn_download)
        
        self.btn_delete = QPushButton("Eliminar Archivo")
        self.btn_delete.setStyleSheet(btn_style)
        self.btn_delete.clicked.connect(self.delete_file)
        layout.addWidget(self.btn_delete)
        
        self.btn_info = QPushButton("Info del Archivo")
        self.btn_info.setStyleSheet(btn_style)
        self.btn_info.clicked.connect(self.show_file_info)
        layout.addWidget(self.btn_info)
        
        self.btn_refresh = QPushButton("Refrescar Lista")
        self.btn_refresh.setStyleSheet(btn_style)
        self.btn_refresh.clicked.connect(self.refresh_files)
        layout.addWidget(self.btn_refresh)
        
        layout.addStretch()
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar archivo:"))
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Ingresar nombre...")
        self.search_box.textChanged.connect(self.filter_files)
        self.search_box.setMaximumWidth(200)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 6px;
                font-size: 11px;
            }
        """)
        search_layout.addWidget(self.search_box)
        
        layout.addLayout(search_layout)
        
        return panel
    
    def create_files_panel(self):
        """Crea el panel de lista de archivos"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Lista de archivos
        self.files_list = QTableWidget()
        self.files_list.setColumnCount(3)
        self.files_list.setHorizontalHeaderLabels(["Nombre del Archivo", "Tamaño", "Bloques"])
        self.files_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_list.setAlternatingRowColors(True)
        
        # Conectar doble click para mostrar información
        self.files_list.doubleClicked.connect(self.on_file_double_click)
        
        layout.addWidget(self.files_list)
        
        return panel
    
    def create_log_panel(self):
        """Crea el panel de logs"""
        panel = QWidget()
        panel.setMaximumHeight(200)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Título de logs
        log_label = QLabel("Sistema de Logs")
        log_label.setStyleSheet("color: #888888; font-size: 11px; padding: 2px 0px;")
        layout.addWidget(log_label)
        
        # Área de logs
        self.log_area = QListWidget()
        self.log_area.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                color: #88cc88;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 4px;
                font-size: 10px;
                outline: none;
            }
            QListWidget::item {
                padding: 2px 6px;
                border-bottom: 1px solid #252525;
            }
            QListWidget::item:selected {
                background-color: #505080;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.log_area)
        
        return panel
    
    def apply_dark_styles(self):
        """Aplica estilos dark theme"""
        self.setStyleSheet("""
            * {
                font-family: 'Verdana', 'Aptos';
                font-size: 11px;
                font-weight: normal;
            }
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #2a2a2a;
            }
            QGroupBox {
                color: #cccccc;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 3px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTableWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                gridline-color: #353535;
                border: 1px solid #404040;
                border-radius: 2px;
                alternate-background-color: #222222;
                outline: none;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #252525;
                color: #e0e0e0;
            }
            QTableWidget::item:selected {
                background-color: #505080;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #cccccc;
                padding: 6px;
                border: none;
                border-right: 1px solid #353535;
                border-bottom: 1px solid #404040;
                font-weight: bold;
            }
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 6px 10px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #404040;
                border: 1px solid #505050;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 6px;
            }
            QLabel {
                color: #cccccc;
            }
        """)
    
    def update_server_label(self):
        """Actualiza la etiqueta del servidor con los valores actuales"""
        self.server_label.setText(f"{self.host}:{self.port}")
        self.server_label.setStyleSheet("font-weight: bold; color: #88aacc;")
    
    def show_connection_dialog(self):
        """Muestra el diálogo de configuración de conexión"""
        dialog = ConnectionDialog(self.host, self.port, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.host = dialog.host
            self.port = dialog.port
            self.update_server_label()  # ¡Aquí estaba el problema! Actualizar la etiqueta
            self.initialize_client()
    
    def reconnect_to_server(self):
        """Reconecta al servidor con la configuración actual"""
        if self.client:
            self.client.close()
        self.initialize_client()
    
    def connect_to_server(self):
        """Conecta al servidor"""
        try:
            if self.client and self.client.connect():
                self.connection_status.setText("CONECTADO")
                self.connection_status.setStyleSheet("""
                    QLabel {
                        padding: 4px 8px;
                        border-radius: 2px;
                        background-color: #2a3a2a;
                        color: #88cc88;
                        font-weight: bold;
                        font-size: 11px;
                        border: 1px solid #335533;
                    }
                """)
                self.update_buttons_state(True)
                self.setWindowTitle(f"File System Manager - {self.host}:{self.port}")
                logger.log("GUI", f"Connection established with server {self.host}:{self.port}")
                self.refresh_files()
                self.update_system_status()
            else:
                self.connection_status.setText("ERROR DE CONEXIÓN")
                self.update_buttons_state(False)
                logger.log("GUI", f"Error: Could not connect to server {self.host}:{self.port}")
        except Exception as e:
            logger.log("GUI", f"Connection error: {str(e)}")
            self.connection_status.setText("ERROR")
            self.update_buttons_state(False)
    
    def disconnect_from_server(self):
        """Desconecta del servidor"""
        try:
            if self.client:
                self.client.close()
                self.connection_status.setText("SIN CONEXIÓN")
                self.connection_status.setStyleSheet("""
                    QLabel {
                        padding: 4px 8px;
                        border-radius: 2px;
                        background-color: #3a2a2a;
                        color: #ff6666;
                        font-weight: bold;
                        font-size: 11px;
                        border: 1px solid #553333;
                    }
                """)
                self.update_buttons_state(False)
                self.setWindowTitle("File System Manager - No conectado")
                # Limpiar lista de archivos
                self.files_list.setRowCount(0)
                # Limpiar estadísticas
                self.clear_statistics()
                logger.log("GUI", "Disconnected from server")
        except Exception as e:
            logger.log("GUI", f"Disconnection error: {str(e)}")
    
    def clear_statistics(self):
        """Limpia las estadísticas del sistema"""
        self.total_files_label.setText("0")
        self.total_blocks_label.setText("0")
        self.used_blocks_label.setText("0")
        self.free_blocks_label.setText("0")
        self.usage_label.setText("0%")
        self.used_space_label.setText("0 MB")
    
    def update_buttons_state(self, connected):
        """Actualiza el estado de los botones según la conexión"""
        self.btn_upload.setEnabled(connected)
        self.btn_download.setEnabled(connected)
        self.btn_delete.setEnabled(connected)
        self.btn_info.setEnabled(connected)
        self.btn_refresh.setEnabled(connected)
        self.btn_refresh_status.setEnabled(connected)
        self.btn_reconnect.setEnabled(True)  # Siempre habilitado
        self.btn_disconnect.setEnabled(connected)
        self.btn_connect.setEnabled(True)  # Siempre habilitado
    
    def on_file_double_click(self, index):
        """Maneja el doble click en un archivo"""
        self.show_file_info()
    
    def upload_file(self):
        """Maneja la subida de archivos"""
        if not self.client or not self.client.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected to server")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select file to upload", "", "All files (*)"
        )
        
        if file_path:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            
            try:
                success = self.client.upload_file(file_path)
                filename = os.path.basename(file_path)
                
                if success:
                    logger.log("GUI", f"Upload successful: {filename}")
                    QMessageBox.information(self, "Success", f"File '{filename}' uploaded successfully")
                    self.refresh_files()
                    self.update_system_status()
                else:
                    logger.log("GUI", f"Upload failed: {filename}")
                    QMessageBox.critical(self, "Error", f"Failed to upload file '{filename}'")
                    
            except Exception as e:
                logger.log("GUI", f"Upload error: {str(e)}")
                QMessageBox.critical(self, "Error", f"Error during upload: {str(e)}")
                # Reconectar en caso de error
                self.reconnect_to_server()
                
            finally:
                self.progress_bar.setVisible(False)
    
    def download_file(self):
        """Maneja la descarga de archivos"""
        if not self.client or not self.client.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected to server")
            return
            
        current_row = self.files_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a file from the list")
            return
        
        filename = self.files_list.item(current_row, 0).text()
        
        save_path = QFileDialog.getExistingDirectory(
            self, "Select destination directory", ""
        )
        
        if save_path:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            
            try:
                success = self.client.download_file(filename, save_path)
                
                if success:
                    logger.log("GUI", f"Download successful: {filename}")
                    QMessageBox.information(self, "Success", f"File '{filename}' downloaded successfully")
                else:
                    logger.log("GUI", f"Download failed: {filename}")
                    QMessageBox.critical(self, "Error", f"Failed to download file '{filename}'")
                    
            except Exception as e:
                logger.log("GUI", f"Download error: {str(e)}")
                QMessageBox.critical(self, "Error", f"Error during download: {str(e)}")
                # Reconectar en caso de error
                self.reconnect_to_server()
                
            finally:
                self.progress_bar.setVisible(False)
    
    def delete_file(self):
        """Maneja la eliminación de archivos"""
        if not self.client or not self.client.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected to server")
            return
            
        current_row = self.files_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a file from the list")
            return
        
        filename = self.files_list.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm deletion",
            f"Are you sure you want to delete '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.client.delete_file(filename):
                    logger.log("GUI", f"File deleted: {filename}")
                    QMessageBox.information(self, "Success", f"File '{filename}' deleted successfully")
                    self.refresh_files()
                    self.update_system_status()
                else:
                    logger.log("GUI", f"Delete failed: {filename}")
                    QMessageBox.critical(self, "Error", f"Failed to delete file '{filename}'")
            except Exception as e:
                logger.log("GUI", f"Delete error: {str(e)}")
                QMessageBox.critical(self, "Error", f"Error during deletion: {str(e)}")
                # Reconectar en caso de error
                self.reconnect_to_server()
    
    def refresh_files(self):
        """Actualiza la lista de archivos"""
        if not self.client or not self.client.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected to server")
            return
            
        try:
            files = self.client.list_files()
            self.update_files_list(files)
            logger.log("GUI", "File list updated")
        except Exception as e:
            logger.log("GUI", f"Error updating list: {str(e)}")
            # Reconectar en caso de error
            self.reconnect_to_server()
    
    def update_files_list(self, files):
        """Actualiza la tabla de archivos"""
        self.files_list.setRowCount(len(files))
        self.current_files_data = files
        
        for row, file_info in enumerate(files):
            # Nombre
            name_item = QTableWidgetItem(file_info['filename'])
            self.files_list.setItem(row, 0, name_item)
            
            # Tamaño (MB)
            size_mb = file_info['size'] / (1024 * 1024)
            size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
            self.files_list.setItem(row, 1, size_item)
            
            # Bloques
            blocks_item = QTableWidgetItem(str(file_info['blocks']))
            self.files_list.setItem(row, 2, blocks_item)
    
    def show_file_info(self, filename=None):
        """Muestra información detallada del archivo en un diálogo secundario"""
        if not self.client or not self.client.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected to server")
            return
            
        if not filename:
            current_row = self.files_list.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Please select a file")
                return
            filename = self.files_list.item(current_row, 0).text()
        
        try:
            info = self.client.get_file_info(filename)
            if info:
                dialog = FileInfoDialog(info, self)
                dialog.exec()
                logger.log("GUI", f"Information displayed: {filename}")
            else:
                QMessageBox.warning(self, "Warning", f"No information found for '{filename}'")
        except Exception as e:
            logger.log("GUI", f"Error getting information: {str(e)}")
            # Reconectar en caso de error
            self.reconnect_to_server()
    
    def update_system_status(self):
        """Actualiza la información del estado del sistema"""
        if not self.client or not self.client.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected to server")
            return
            
        try:
            status = self.client.get_storage_status()
            if status:
                # Actualizar etiquetas
                self.total_files_label.setText(str(status['file_count']))
                self.total_blocks_label.setText(str(status['total_blocks']))
                self.used_blocks_label.setText(str(status['used_blocks']))
                self.free_blocks_label.setText(str(status['free_blocks']))
                self.usage_label.setText(f"{status['usage_percent']:.1f}%")
                
                # Formatear espacio usado
                used_space_mb = status['total_files_size'] / (1024 * 1024)
                self.used_space_label.setText(f"{used_space_mb:.2f} MB")
                
                logger.log("GUI", "System status updated")
        except Exception as e:
            logger.log("GUI", f"Error getting system status: {str(e)}")
            # Reconectar en caso de error
            self.reconnect_to_server()
    
    def filter_files(self, text):
        """Filtra la lista de archivos según el texto de búsqueda"""
        for row in range(self.files_list.rowCount()):
            item = self.files_list.item(row, 0)
            if item:
                match = text.lower() in item.text().lower()
                self.files_list.setRowHidden(row, not match)
    
    def closeEvent(self, event):
        """Maneja el cierre de la aplicación"""
        if self.client:
            self.client.close()
        event.accept()

def main():
    """Función principal"""
    app = QApplication(sys.argv)
    
    # Mensaje de inicio
    logger.log("SYSTEM", "File System Manager iniciado")
    
    # Crear y mostrar la ventana principal
    window = FileManagerGUI()
    window.show()
    
    logger.log("SYSTEM", "GUI iniciada - Use 'Conectar' para configurar el servidor")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()