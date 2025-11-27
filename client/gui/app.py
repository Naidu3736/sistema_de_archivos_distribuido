import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QMessageBox, QDialog, QTableWidgetItem)
from PyQt6.QtCore import Qt
from client.file_client import FileClient
from core.logger import logger
from client.gui.dialogs import (ConnectionDialog, FileInfoDialog, BlockTableDialog)
from client.gui.panels import LeftPanel, RightPanel
from client.gui.threads import ConnectionThread

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
        self.left_panel = LeftPanel(self)
        main_layout.addWidget(self.left_panel)
        
        # Panel derecho - Contenido principal
        self.right_panel = RightPanel(self)
        main_layout.addWidget(self.right_panel)
        
        # Aplicar estilo
        self.apply_dark_styles()
    
    def setup_logger_connection(self):
        """Conecta el logger al área de logs de la interfaz"""
        logger.set_ui_callback(self.add_log_to_ui)
    
    def add_log_to_ui(self, log_entry):
        """Agrega un mensaje del logger al área de logs de la UI"""
        self.right_panel.log_area.addItem(log_entry)
        # Auto-scroll al final
        self.right_panel.log_area.scrollToBottom()
    
    def initialize_client(self):
        """Inicializa el cliente con los parámetros de conexión actuales"""
        try:
            if self.client:
                self.client.close()
                
            self.client = FileClient(self.host, self.port)
            self.connect_to_server()
        except Exception as e:
            logger.log("GUI", f"Error inicializando cliente: {str(e)}")
            self.left_panel.connection_status.setText("Error de Inicio")
    
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
        self.left_panel.server_label.setText(f"{self.host}:{self.port}")
        self.left_panel.server_label.setStyleSheet("font-weight: bold; color: #88aacc;")
    
    def show_connection_dialog(self):
        """Muestra el diálogo de configuración de conexión"""
        dialog = ConnectionDialog(self.host, self.port, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.host = dialog.host
            self.port = dialog.port
            self.update_server_label()
            self.initialize_client()
    
    def reconnect_to_server(self):
        """Reconecta al servidor con la configuración actual"""
        if self.client:
            self.client.close()
        self.initialize_client()
    
    def connect_to_server(self):
        """Conecta al servidor usando un hilo en segundo plano"""
        if not self.client:
            return

        # Actualizar UI para mostrar estado de conexión
        self.left_panel.connection_status.setText("CONECTANDO...")
        self.left_panel.connection_status.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                border-radius: 2px;
                background-color: #3a3a2a;
                color: #dddd88;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #555533;
            }
        """)
        self.update_buttons_state(False)
        self.left_panel.btn_connect.setEnabled(False)  # Deshabilitar conectar mientras conecta
        
        # Iniciar hilo de conexión
        self.connection_thread = ConnectionThread(self.client)
        self.connection_thread.connection_success.connect(self.on_connection_success)
        self.connection_thread.connection_failed.connect(self.on_connection_failed)
        self.connection_thread.connection_error.connect(self.on_connection_error)
        self.connection_thread.start()

    def on_connection_success(self):
        """Maneja la conexión exitosa"""
        self.left_panel.connection_status.setText("CONECTADO")
        self.left_panel.connection_status.setStyleSheet("""
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

    def on_connection_failed(self):
        """Maneja el fallo de conexión"""
        self.left_panel.connection_status.setText("ERROR CONEXIÓN")
        self.left_panel.connection_status.setStyleSheet("""
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
        self.setWindowTitle("File System Manager - Error de Conexión")
        logger.log("GUI", f"Failed to connect to server {self.host}:{self.port}")

    def on_connection_error(self, error_msg):
        """Maneja errores durante la conexión"""
        logger.log("GUI", f"Connection error: {error_msg}")
        self.left_panel.connection_status.setText("ERROR")
        self.update_buttons_state(False)

    def disconnect_from_server(self):
        """Desconecta del servidor"""
        if self.client:
            self.client.disconnect()
            self.left_panel.connection_status.setText("DESCONECTADO")
            self.left_panel.connection_status.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    border-radius: 2px;
                    background-color: #3a3a2a;
                    color: #aaaaaa;
                    font-weight: bold;
                    font-size: 11px;
                    border: 1px solid #555555;
                }
            """)
            self.update_buttons_state(False)
            self.setWindowTitle("File System Manager - Desconectado")
            
            # Limpiar UI
            self.right_panel.files_list.setRowCount(0)
            self.left_panel.total_files_label.setText("0")
            self.left_panel.total_blocks_label.setText("0")
            self.left_panel.used_blocks_label.setText("0")
            self.left_panel.free_blocks_label.setText("0")
            self.left_panel.usage_label.setText("0%")
            self.left_panel.used_space_label.setText("0 MB")
    
    def show_block_table(self):
        """Muestra la tabla de bloques del servidor"""
        if not self.client or not self.client.is_connected:
            QMessageBox.warning(self, "Error", "No hay conexión con el servidor")
            return
            
        try:
            # Obtener datos del servidor
            block_table_data = self.client.get_block_table()
            
            if not block_table_data:
                QMessageBox.information(self, "Info", "La tabla de bloques está vacía o hubo un error al recibirla")
                return
                
            # Mostrar diálogo
            dialog = BlockTableDialog(block_table_data, self)
            dialog.exec()
            
        except Exception as e:
            logger.log("GUI", f"Error mostrando tabla de bloques: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al obtener tabla de bloques: {str(e)}")

    def update_buttons_state(self, connected):
        """Actualiza el estado de los botones según la conexión"""
        self.right_panel.btn_upload.setEnabled(connected)
        self.right_panel.btn_download.setEnabled(connected)
        self.right_panel.btn_delete.setEnabled(connected)
        self.right_panel.btn_info.setEnabled(connected)
        self.right_panel.btn_refresh.setEnabled(connected)
        self.left_panel.btn_disconnect.setEnabled(connected)
        self.left_panel.btn_reconnect.setEnabled(True)  # Siempre habilitado
        self.left_panel.btn_connect.setEnabled(not connected)
        self.right_panel.btn_block_table.setEnabled(connected)
        
        # Estilos para botones deshabilitados/habilitados
        disabled_style = """
            QPushButton {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #353535;
                padding: 8px 12px;
                border-radius: 3px;
                font-size: 11px;
                min-width: 100px;
            }
        """
        
        enabled_style = """
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
        """
        
        for btn in [self.right_panel.btn_upload, self.right_panel.btn_download, self.right_panel.btn_delete, 
                   self.right_panel.btn_info, self.right_panel.btn_refresh, self.right_panel.btn_block_table]:
            btn.setStyleSheet(enabled_style if connected else disabled_style)

    def refresh_files(self):
        """Actualiza la lista de archivos"""
        if not self.client or not self.client.is_connected:
            return
            
        try:
            files = self.client.list_files()
            self.current_files_data = files
            self.update_files_table(files)
            self.update_system_status()
        except Exception as e:
            logger.log("GUI", f"Error refreshing files: {str(e)}")
            
    def update_files_table(self, files):
        """Actualiza la tabla de archivos con los datos recibidos"""
        self.right_panel.files_list.setRowCount(len(files))
        
        for row, file_data in enumerate(files):
            # Nombre
            name_item = QTableWidgetItem(file_data['filename'])
            self.right_panel.files_list.setItem(row, 0, name_item)
            
            # Tamaño
            size_mb = file_data['size'] / (1024 * 1024)
            size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
            self.right_panel.files_list.setItem(row, 1, size_item)
            
            # Bloques
            blocks_item = QTableWidgetItem(str(file_data.get('block_count', 0)))
            self.right_panel.files_list.setItem(row, 2, blocks_item)
            
        self.left_panel.total_files_label.setText(str(len(files)))

    def filter_files(self, text):
        """Filtra la lista de archivos según el texto de búsqueda"""
        if not self.current_files_data:
            return
            
        filtered_files = [
            f for f in self.current_files_data 
            if text.lower() in f['filename'].lower()
        ]
        self.update_files_table(filtered_files)

    def on_file_double_click(self, index):
        """Maneja el doble click en un archivo"""
        self.show_file_info()

    def get_selected_filename(self):
        """Obtiene el nombre del archivo seleccionado"""
        selected_items = self.right_panel.files_list.selectedItems()
        if not selected_items:
            return None
        # La primera columna es el nombre
        return self.right_panel.files_list.item(selected_items[0].row(), 0).text()

    def upload_file(self):
        """Maneja la subida de archivos"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo para Subir")
        
        if file_path:
            # Mostrar progreso indeterminado
            self.right_panel.progress_bar.setVisible(True)
            self.right_panel.progress_bar.setRange(0, 0)  # Indeterminado
            
            try:
                success = self.client.upload_file(file_path)
                if success:
                    QMessageBox.information(self, "Éxito", "Archivo subido correctamente")
                    self.refresh_files()
                else:
                    QMessageBox.warning(self, "Error", "Error al subir el archivo")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Excepción al subir: {str(e)}")
            finally:
                self.right_panel.progress_bar.setVisible(False)

    def download_file(self):
        """Maneja la descarga de archivos"""
        filename = self.get_selected_filename()
        if not filename:
            QMessageBox.warning(self, "Aviso", "Por favor seleccione un archivo para descargar")
            return
            
        from PyQt6.QtWidgets import QFileDialog
        save_path = QFileDialog.getExistingDirectory(
            self, 
            "Guardar Archivo",
            ""
        )
        
        if save_path:
            self.right_panel.progress_bar.setVisible(True)
            self.right_panel.progress_bar.setRange(0, 0)
            
            try:
                success = self.client.download_file(filename, save_path)
                if success:
                    QMessageBox.information(self, "Éxito", "Archivo descargado correctamente")
                else:
                    QMessageBox.warning(self, "Error", "Error al descargar el archivo")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Excepción al descargar: {str(e)}")
            finally:
                self.right_panel.progress_bar.setVisible(False)

    def delete_file(self):
        """Maneja la eliminación de archivos"""
        filename = self.get_selected_filename()
        if not filename:
            QMessageBox.warning(self, "Aviso", "Por favor seleccione un archivo para eliminar")
            return
            
        confirm = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Está seguro de eliminar el archivo '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                success = self.client.delete_file(filename)
                if success:
                    QMessageBox.information(self, "Éxito", "Archivo eliminado correctamente")
                    self.refresh_files()
                else:
                    QMessageBox.warning(self, "Error", "Error al eliminar el archivo")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Excepción al eliminar: {str(e)}")

    def show_file_info(self):
        """Muestra información detallada del archivo"""
        filename = self.get_selected_filename()
        if not filename:
            QMessageBox.warning(self, "Aviso", "Por favor seleccione un archivo")
            return
            
        try:
            info = self.client.get_file_info(filename)
            if info:
                dialog = FileInfoDialog(info, self)
                dialog.exec()
            else:
                QMessageBox.warning(self, "Error", "No se pudo obtener información del archivo")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al obtener información: {str(e)}")

    def update_system_status(self):
        """Actualiza las estadísticas del sistema"""
        if not self.client or not self.client.is_connected:
            return
            
        try:
            status = self.client.get_storage_status()
            if status:
                self.left_panel.total_blocks_label.setText(str(status['total_blocks']))
                self.left_panel.used_blocks_label.setText(str(status['used_blocks']))
                self.left_panel.free_blocks_label.setText(str(status['free_blocks']))
                
                # Calcular porcentaje
                if status['total_blocks'] > 0:
                    usage_pct = (status['used_blocks'] / status['total_blocks']) * 100
                    self.left_panel.usage_label.setText(f"{usage_pct:.1f}%")
                    
                    # Color según uso
                    if usage_pct > 90:
                        self.left_panel.usage_label.setStyleSheet("font-weight: bold; color: #ff6666;")
                    elif usage_pct > 70:
                        self.left_panel.usage_label.setStyleSheet("font-weight: bold; color: #ffcc66;")
                    else:
                        self.left_panel.usage_label.setStyleSheet("font-weight: bold; color: #88cc88;")
                
                # Espacio usado (estimado)
                block_size = 4096  # Asumimos 4KB por bloque
                used_mb = (status['used_blocks'] * block_size) / (1024 * 1024)
                self.left_panel.used_space_label.setText(f"{used_mb:.2f} MB")
                
        except Exception as e:
            logger.log("GUI", f"Error updating status: {str(e)}")
