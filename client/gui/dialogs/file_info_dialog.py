from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QMessageBox, QTextEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class FileInfoDialog(QDialog):
    """Diálogo para mostrar información detallada del archivo"""
    def __init__(self, file_info, parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Información del Archivo")
        self.setGeometry(200, 200, 800, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Información básica del archivo
        info_text = f"""
        <h3>Información del Archivo</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold; width: 120px;">Nombre:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['filename']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">Tamaño:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['size'] / (1024 * 1024):.2f} MB</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">Cantidad de Bloques:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['block_count']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #404040; font-weight: bold;">Primer Bloque:</td>
                <td style="padding: 8px; border-bottom: 1px solid #404040;">{self.file_info['first_block_id']}</td>
            </tr>
        </table>
        """
        
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        self.info_display.setHtml(info_text)
        self.info_display.setFixedHeight(180)
        self.info_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #cccccc;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 12px;
                font-size: 12px;
                selection-background-color: #505080;
            }
        """)
        layout.addWidget(self.info_display)
        
        # Tabla de Block Chain
        layout.addWidget(QLabel("<h4>Cadena de Bloques</h4>"))
        self.create_block_chain_table(layout)
        
        # Botón de cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #404040;
                border: 1px solid #505050;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
    
    def create_block_chain_table(self, layout):
        """Crea la tabla para mostrar la cadena de bloques"""
        self.block_table = QTableWidget()
        
        # Configurar columnas
        headers = ["Bloque Lógico", "Bloque Físico", "Nodo Primario", "Nodos Réplicas"]
        self.block_table.setColumnCount(len(headers))
        self.block_table.setHorizontalHeaderLabels(headers)
        
        # Obtener y procesar la cadena de bloques
        block_chain_data = self.file_info['block_chain']
        
        self.block_table.setRowCount(len(block_chain_data))
        
        # Llenar la tabla con datos
        for row, block_data in enumerate(block_chain_data):
            # block_data es una tupla: (logical, physical, primary_node, replica_nodes)
            logical_block, physical_block, primary_node, replica_nodes = block_data
            
            # Bloque Lógico
            logical_item = QTableWidgetItem(str(logical_block))
            logical_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Bloque Físico
            physical_item = QTableWidgetItem(str(physical_block))
            physical_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Nodo Primario
            primary_item = QTableWidgetItem(str(primary_node) if primary_node is not None else "N/A")
            primary_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Nodos Réplicas
            replicas_text = ", ".join(map(str, replica_nodes)) if replica_nodes else "Sin réplicas"
            replicas_item = QTableWidgetItem(replicas_text)
            replicas_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Agregar items a la tabla
            self.block_table.setItem(row, 0, logical_item)
            self.block_table.setItem(row, 1, physical_item)
            self.block_table.setItem(row, 2, primary_item)
            self.block_table.setItem(row, 3, replicas_item)
            
            # Colorear filas alternas para mejor legibilidad
            if row % 2 == 0:
                for col in range(self.block_table.columnCount()):
                    item = self.block_table.item(row, col)
                    if item:
                        item.setBackground(QColor(30, 30, 30))
        
        # Configurar estilo de la tabla
        self.block_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                gridline-color: #404040;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #2a2a2a;
            }
            QTableWidget::item:selected {
                background-color: #3a6da4;
                color: white;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #e0e0e0;
                padding: 8px;
                border: none;
                border-right: 1px solid #404040;
                border-bottom: 1px solid #404040;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        
        # Ajustar el tamaño de las columnas
        header = self.block_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Bloque Lógico
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Bloque Físico
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Nodo Primario
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Nodos Réplicas (ocupa espacio restante)
        
        # Configurar tamaño de la tabla
        self.block_table.setMinimumHeight(250)
        layout.addWidget(self.block_table)