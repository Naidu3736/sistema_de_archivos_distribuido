from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QMessageBox, QTextEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

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