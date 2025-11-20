# client_gui.py
import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QListWidget, QTextEdit,
                            QLabel, QProgressBar, QFileDialog, QMessageBox,
                            QTabWidget, QGroupBox, QLineEdit, QSplitter,
                            QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
from client.file_client import FileClient
from core.logger import logger

class FileUploadThread(QThread):
    """Hilo para subir archivos sin bloquear la UI"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, client, file_path):
        super().__init__()
        self.client = client
        self.file_path = file_path
    
    def run(self):
        try:
            success = self.client.upload_file(self.file_path)
            self.finished.emit(success, os.path.basename(self.file_path))
        except Exception as e:
            self.finished.emit(False, str(e))

class FileDownloadThread(QThread):
    """Hilo para descargar archivos"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, client, filename, save_path):
        super().__init__()
        self.client = client
        self.filename = filename
        self.save_path = save_path
    
    def run(self):
        try:
            success = self.client.download_file(self.filename, self.save_path)
            self.finished.emit(success, self.filename)
        except Exception as e:
            self.finished.emit(False, str(e))

class FileManagerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = None
        self.host = "localhost"
        self.port = 8001
        self.current_files_data = []
        self.init_ui()
        self.setup_logger_connection()
        self.connect_to_server()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("File System Manager")
        self.setGeometry(100, 100, 1000, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(1)
        
        # Panel izquierdo - Navegación
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Panel derecho - Contenido
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)
        
        # Aplicar estilo
        self.apply_dark_styles()
    
    def setup_logger_connection(self):
        """Conecta el logger al área de logs de la interfaz"""
        logger.set_ui_callback(self.add_log_to_ui)
        logger.log("GUI", "Logger conectado a la interfaz de usuario")
    
    def add_log_to_ui(self, log_entry):
        """Agrega un mensaje del logger al área de logs de la UI"""
        self.log_area.addItem(log_entry)
        # Auto-scroll al final
        self.log_area.scrollToBottom()
    
    def create_left_panel(self):
        """Crea el panel de navegación izquierdo"""
        panel = QWidget()
        panel.setMaximumWidth(200)
        panel.setMinimumWidth(180)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(8)
        
        # Título
        title = QLabel("FILE SYSTEM")
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
        
        # Botones de operaciones
        btn_style = """
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 10px 8px;
                border-radius: 3px;
                font-size: 12px;
                text-align: left;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #404040;
                border: 1px solid #505050;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
                border: 1px solid #606060;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #353535;
            }
        """
        
        self.btn_upload = QPushButton("Upload File")
        self.btn_upload.setStyleSheet(btn_style)
        self.btn_upload.clicked.connect(self.upload_file)
        layout.addWidget(self.btn_upload)
        
        self.btn_download = QPushButton("Download File")
        self.btn_download.setStyleSheet(btn_style)
        self.btn_download.clicked.connect(self.download_file)
        layout.addWidget(self.btn_download)
        
        self.btn_delete = QPushButton("Delete File")
        self.btn_delete.setStyleSheet(btn_style)
        self.btn_delete.clicked.connect(self.delete_file)
        layout.addWidget(self.btn_delete)
        
        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.setStyleSheet(btn_style)
        self.btn_refresh.clicked.connect(self.refresh_files)
        layout.addWidget(self.btn_refresh)
        
        self.btn_info = QPushButton("File Information")
        self.btn_info.setStyleSheet(btn_style)
        self.btn_info.clicked.connect(self.show_file_info)
        layout.addWidget(self.btn_info)
        
        self.btn_status = QPushButton("System Status")
        self.btn_status.setStyleSheet(btn_style)
        self.btn_status.clicked.connect(self.show_system_status)
        layout.addWidget(self.btn_status)
        
        # Separador
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #404040;")
        layout.addWidget(separator)
        
        # Estado de conexión
        connection_layout = QVBoxLayout()
        connection_label = QLabel("Connection Status")
        connection_label.setStyleSheet("color: #888888; font-size: 11px; padding: 5px 0px;")
        connection_layout.addWidget(connection_label)
        
        self.connection_status = QLabel("DISCONNECTED")
        self.connection_status.setStyleSheet("""
            QLabel {
                padding: 8px 5px;
                border-radius: 2px;
                background-color: #3a2a2a;
                color: #ff6666;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #553333;
            }
        """)
        connection_layout.addWidget(self.connection_status)
        layout.addLayout(connection_layout)
        
        layout.addStretch()
        return panel
    
    def create_right_panel(self):
        """Crea el panel de contenido derecho"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        
        # Tabs para diferentes vistas
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Tab 1: Lista de archivos
        self.files_tab = self.create_files_tab()
        self.tabs.addTab(self.files_tab, "Files")
        
        # Tab 2: Información detallada
        self.info_tab = self.create_info_tab()
        self.tabs.addTab(self.info_tab, "Information")
        
        # Tab 3: Estado del sistema
        self.status_tab = self.create_status_tab()
        self.tabs.addTab(self.status_tab, "System Status")
        
        layout.addWidget(self.tabs)
        
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
            }
            QProgressBar::chunk {
                background-color: #505080;
                border-radius: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Área de logs
        log_label = QLabel("System Log")
        log_label.setStyleSheet("color: #888888; font-size: 11px; padding: 5px 0px;")
        layout.addWidget(log_label)
        
        self.log_area = QListWidget()
        self.log_area.setMaximumHeight(240)
        self.log_area.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                color: #88cc88;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 4px;
                font-size: 11px;
                outline: none;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
            QListWidget::item:selected {
                background-color: #505080;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.log_area)
        
        return panel
    
    def create_files_tab(self):
        """Crea la pestaña de lista de archivos"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search files...")
        self.search_box.textChanged.connect(self.filter_files)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 8px;
                font-size: 12px;
                selection-background-color: #505080;
            }
            QLineEdit:focus {
                border: 1px solid #606080;
            }
        """)
        search_layout.addWidget(self.search_box)
        
        self.btn_clear_search = QPushButton("Clear")
        self.btn_clear_search.setStyleSheet("""
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        self.btn_clear_search.clicked.connect(self.clear_search)
        search_layout.addWidget(self.btn_clear_search)
        layout.addLayout(search_layout)
        
        # Lista de archivos
        self.files_list = QTableWidget()
        self.files_list.setColumnCount(3)
        self.files_list.setHorizontalHeaderLabels(["Filename", "Size", "Blocks"])
        self.files_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_list.setAlternatingRowColors(True)
        layout.addWidget(self.files_list)
        
        return widget
    
    def create_info_tab(self):
        """Crea la pestaña de información"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
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
        
        return widget
    
    def create_status_tab(self):
        """Crea la pestaña de estado del sistema"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Información del sistema
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setStyleSheet("""
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
        layout.addWidget(self.status_display)
        
        # Botón para actualizar estado
        self.btn_refresh_status = QPushButton("Refresh Status")
        self.btn_refresh_status.setStyleSheet("""
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        self.btn_refresh_status.clicked.connect(self.update_system_status)
        layout.addWidget(self.btn_refresh_status)
        
        return widget
    
    def apply_dark_styles(self):
        """Aplica estilos dark theme tipo Photoshop"""
        self.setStyleSheet("""
            * {
                font-family: 'Verdana', 'Aptos';
                font-size: 12px;
                font-weight: normal;
            }
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #2a2a2a;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #2a2a2a;
                border-radius: 0px;
            }
            QTabBar::tab {
                background-color: #363636;
                color: #cccccc;
                padding: 8px 16px;
                margin-right: 1px;
                border: 1px solid #404040;
                border-bottom: none;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border-bottom: 1px solid #2a2a2a;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
            }
            QTableWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                gridline-color: #353535;
                border: 1px solid #404040;
                border-radius: 2px;
                alternate-background-color: #222222;
                outline: none;
                font-weight: 500;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #252525;
                color: #e0e0e0;
                border: none;
                outline: none;
            }
            QTableWidget::item:selected {
                background-color: #505080;
                color: #ffffff;
                border: none;
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #cccccc;
                padding: 8px;
                border: none;
                border-right: 1px solid #353535;
                border-bottom: 1px solid #404040;
                font-weight: bold;
                font-weight: 500;
            }
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 6px 12px;
                border-radius: 2px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #404040;
                border: 1px solid #505050;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 8px;
                selection-background-color: #505080;
            }
            QLineEdit:focus {
                border: 1px solid #606080;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #cccccc;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 12px;
                selection-background-color: #505080;
            }
            QLabel {
                color: #cccccc;
            }
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 2px;
                text-align: center;
                background-color: #2a2a2a;
                color: #cccccc;
            }
            QProgressBar::chunk {
                background-color: #505080;
                border-radius: 1px;
            }
        """)
    
    def connect_to_server(self):
        """Conecta al servidor"""
        try:
            self.client = FileClient(self.host, self.port)
            if self.client.connect():
                self.connection_status.setText("CONNECTED")
                self.connection_status.setStyleSheet("""
                    QLabel {
                        padding: 8px 5px;
                        border-radius: 2px;
                        background-color: #2a3a2a;
                        color: #88cc88;
                        font-weight: bold;
                        font-size: 11px;
                        border: 1px solid #335533;
                    }
                """)
                logger.log("GUI", "Connection established with server")
                self.refresh_files()
            else:
                self.connection_status.setText("CONNECTION ERROR")
                logger.log("GUI", "Error: Could not connect to server")
        except Exception as e:
            logger.log("GUI", f"Connection error: {str(e)}")
    
    def log_message(self, message):
        """Agrega un mensaje al área de logs"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_area.append(formatted_message)
        logger.log("GUI", message)
    
    def upload_file(self):
        """Maneja la subida de archivos"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select file to upload", "", "All files (*)"
        )
        
        if file_path:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            
            self.upload_thread = FileUploadThread(self.client, file_path)
            self.upload_thread.finished.connect(self.upload_finished)
            self.upload_thread.start()
            
            logger.log("GUI", f"Starting upload: {os.path.basename(file_path)}")
    
    def upload_finished(self, success, filename):
        """Callback cuando termina la subida"""
        self.progress_bar.setVisible(False)
        if success:
            logger.log("GUI", f"Upload successful: {filename}")
            QMessageBox.information(self, "Success", f"File '{filename}' uploaded successfully")
            self.refresh_files()
        else:
            logger.log("GUI", f"Upload failed: {filename}")
            QMessageBox.critical(self, "Error", f"Failed to upload file '{filename}'")
    
    def download_file(self):
        """Maneja la descarga de archivos"""
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
            
            self.download_thread = FileDownloadThread(
                self.client, filename, save_path
            )
            self.download_thread.finished.connect(self.download_finished)
            self.download_thread.start()
            
            logger.log("GUI", f"Starting download: {filename}")
    
    def download_finished(self, success, filename):
        """Callback cuando termina la descarga"""
        self.progress_bar.setVisible(False)
        if success:
            logger.log("GUI", f"Download successful: {filename}")
            QMessageBox.information(self, "Success", f"File '{filename}' downloaded successfully")
        else:
            logger.log("GUI", f"Download failed: {filename}")
            QMessageBox.critical(self, "Error", f"Failed to download file '{filename}'")
    
    def delete_file(self):
        """Maneja la eliminación de archivos"""
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
            if self.client.delete_file(filename):
                logger.log("GUI", f"File deleted: {filename}")
                QMessageBox.information(self, "Success", f"File '{filename}' deleted successfully")
                self.refresh_files()
            else:
                logger.log("GUI", f"Delete failed: {filename}")
                QMessageBox.critical(self, "Error", f"Failed to delete file '{filename}'")
    
    def refresh_files(self):
        """Actualiza la lista de archivos"""
        try:
            files = self.client.list_files()
            self.update_files_list(files)
            logger.log("GUI", "File list updated")
        except Exception as e:
            logger.log("GUI", f"Error updating list: {str(e)}")
    
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
    
    def show_file_info_from_row(self, row):
        """Muestra información del archivo desde una fila específica"""
        filename = self.files_list.item(row, 0).text()
        self.show_file_info(filename)
    
    def show_file_info(self, filename=None):
        """Muestra información detallada del archivo"""
        if not filename:
            current_row = self.files_list.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Please select a file")
                return
            filename = self.files_list.item(current_row, 0).text()
        
        try:
            info = self.client.get_file_info(filename)
            if info:
                self.tabs.setCurrentIndex(1)
                
                info_text = f"""FILE INFORMATION
Name: {info['filename']}
Size: {info['size'] / (1024 * 1024):.2f} MB
Blocks: {info['block_count']}
First Block: {info['first_block_id']}
Block Chain: {info['block_chain']}"""
                self.info_display.setText(info_text)
                logger.log("GUI", f"Information displayed: {filename}")
            else:
                QMessageBox.warning(self, "Warning", f"No information found for '{filename}'")
        except Exception as e:
            logger.log("GUI", f"Error getting information: {str(e)}")
    
    def show_system_status(self):
        """Muestra el estado del sistema"""
        self.tabs.setCurrentIndex(2)
        self.update_system_status()
    
    def update_system_status(self):
        """Actualiza la información del estado del sistema"""
        try:
            status = self.client.get_storage_status()
            if status:
                status_text = f"""SYSTEM STATUS
Total Blocks: {status['total_blocks']}
Used Blocks: {status['used_blocks']}
Free Blocks: {status['free_blocks']}
Usage: {status['usage_percent']:.1f}%
Files: {status['file_count']}
Used Space: {status['total_files_size'] / (1024 * 1024):.2f} MB"""
                self.status_display.setText(status_text)
                logger.log("GUI", "System status updated")
        except Exception as e:
            logger.log("GUI", f"Error getting system status: {str(e)}")
    
    def filter_files(self, text):
        """Filtra la lista de archivos según el texto de búsqueda"""
        for row in range(self.files_list.rowCount()):
            item = self.files_list.item(row, 0)
            if item:
                match = text.lower() in item.text().lower()
                self.files_list.setRowHidden(row, not match)
    
    def clear_search(self):
        """Limpia la búsqueda"""
        self.search_box.clear()
        for row in range(self.files_list.rowCount()):
            self.files_list.setRowHidden(row, False)

def main():
    """Función principal"""
    app = QApplication(sys.argv)
    
    # Mensaje de inicio
    logger.log("SYSTEM", "File System Manager iniciado")
    
    # Configuración inicial
    from PyQt6.QtWidgets import QInputDialog
    host, ok = QInputDialog.getText(
        None, "Server Configuration", 
        "Server:", text="localhost"
    )
    if not ok:
        return
    
    port, ok = QInputDialog.getInt(
        None, "Server Configuration",
        "Port:", value=8001, min=1, max=65535
    )
    if not ok:
        return
    
    # Crear y mostrar la ventana principal
    window = FileManagerGUI()
    window.host = host
    window.port = port
    window.show()
    
    logger.log("SYSTEM", f"GUI iniciada - Servidor: {host}:{port}")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()