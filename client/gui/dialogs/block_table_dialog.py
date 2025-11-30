from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QMessageBox, QTextEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class BlockTableDialog(QDialog):
    """Diálogo para mostrar la tabla de bloques del servidor"""
    def __init__(self, block_table_data, parent=None):
        super().__init__(parent)
        self.block_table_data = block_table_data
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Server Block Table")
        self.setGeometry(150, 150, 800, 500)
        
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("Tabla de Bloques")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #cccccc; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Tabla de bloques
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Bloque Lógico", "Bloque Físico", "Estado", "Nodo Primario", "Replicas", "Siguiente Bloque"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Llenar datos
        self.table.setRowCount(len(self.block_table_data))
        for row, block in enumerate(self.block_table_data):
            # Logical ID
            self.table.setItem(row, 0, QTableWidgetItem(str(block.get('logical_id', ''))))
            
            # Physical ID
            phys_id = block.get('physical_number')
            self.table.setItem(row, 1, QTableWidgetItem(str(phys_id) if phys_id is not None else "-"))
            
            # Status
            status = "Allocated" if block.get('physical_number') is not None else "Free"
            status_item = QTableWidgetItem(status)
            if status == "Allocated":
                status_item.setForeground(QColor("#88cc88"))
            else:
                status_item.setForeground(QColor("#888888"))
            self.table.setItem(row, 2, status_item)
            
            # Primary Node
            primary = block.get('primary_node')
            self.table.setItem(row, 3, QTableWidgetItem(str(primary) if primary is not None else "-"))
            
            # Replicas
            replicas = block.get('replica_nodes', [])
            self.table.setItem(row, 4, QTableWidgetItem(str(replicas) if replicas else "-"))
            
            # Next Block
            next_b = block.get('next_block')
            self.table.setItem(row, 5, QTableWidgetItem(str(next_b) if next_b is not None else "-"))
            
        layout.addWidget(self.table)
        
        # Botón cerrar
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 8px 12px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Estilos
        self.setStyleSheet("""
            QDialog { background-color: #2a2a2a; }
            QLabel { color: #cccccc; }
            QTableWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                gridline-color: #353535;
                border: 1px solid #404040;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #cccccc;
                padding: 4px;
                border: 1px solid #353535;
            }
        """)
