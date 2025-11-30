from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGroupBox)
from PyQt6.QtCore import Qt

class LeftPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
        
    def init_ui(self):
        self.setMaximumWidth(300)
        self.setMinimumWidth(280)
        layout = QVBoxLayout(self)
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
        self.server_label = QLabel("No configurado")
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
        self.btn_connect.clicked.connect(self.main_window.show_connection_dialog)
        connection_buttons_layout.addWidget(self.btn_connect)
        
        self.btn_reconnect = QPushButton("Reconectar")
        self.btn_reconnect.clicked.connect(self.main_window.reconnect_to_server)
        connection_buttons_layout.addWidget(self.btn_reconnect)
        
        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.clicked.connect(self.main_window.disconnect_from_server)
        connection_buttons_layout.addWidget(self.btn_disconnect)
        
        # Estilos botones
        btn_style = """
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
        """
        self.btn_reconnect.setStyleSheet(btn_style)
        
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
        self.btn_refresh_status.clicked.connect(self.main_window.update_system_status)
        layout.addWidget(self.btn_refresh_status)
        
        layout.addStretch()
