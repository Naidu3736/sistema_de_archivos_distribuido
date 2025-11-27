from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QHeaderView, QProgressBar, 
                            QListWidget, QLineEdit)
from PyQt6.QtCore import Qt

class RightPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
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
        
    def create_actions_panel(self):
        """Crea la barra de acciones superiores"""
        panel = QWidget()
        panel.setMaximumHeight(100)  
        panel.setObjectName("actionsPanel")  
        
        main_layout = QVBoxLayout(panel)  
        main_layout.setContentsMargins(15, 8, 15, 8)  
        main_layout.setSpacing(8)
        
        # Fila de búsqueda
        search_row = QHBoxLayout()
        search_row.addStretch()  
        
        search_container = QWidget()
        search_container.setFixedHeight(32)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)
        search_layout.addStretch()
        
        search_label = QLabel("Buscar archivo:")
        search_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        search_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Ingresar nombre...")
        self.search_box.textChanged.connect(self.main_window.filter_files)
        self.search_box.setFixedWidth(250)
        self.search_box.setFixedHeight(28)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
                selection-background-color: #3a6da4;
            }
            QLineEdit:focus {
                border: 1px solid #5070a0;
                background-color: #2d2d2d;
            }
        """)
        search_layout.addWidget(self.search_box)
        
        search_row.addWidget(search_container)
        main_layout.addLayout(search_row)
        
        # Fila de botones
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)  # Espaciado entre botones
        
        # Estilo mejorado para botones
        btn_style = """
            QPushButton {
                background-color: #363636;
                color: #e0e0e0;
                border: 1px solid #454545;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                min-width: 110px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #404040;
                border: 1px solid #505050;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
                padding: 9px 16px 7px 16px;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #353535;
            }
            QPushButton:focus {
                border: 1px solid #5070a0;
            }
        """
        
        # Crear botones con tooltips
        buttons_config = [
            ("Subir Archivo", self.main_window.upload_file, "Subir un nuevo archivo al sistema"),
            ("Descargar Archivo", self.main_window.download_file, "Descargar el archivo seleccionado"),
            ("Eliminar Archivo", self.main_window.delete_file, "Eliminar el archivo seleccionado"),
            ("Info del Archivo", self.main_window.show_file_info, "Mostrar información del archivo"),
            ("Tabla de Bloques", self.main_window.show_block_table, "Mostrar tabla de bloques del sistema"),
            ("Refrescar Lista", self.main_window.refresh_files, "Actualizar la lista de archivos")
        ]
        
        for text, slot, tooltip in buttons_config:
            btn = QPushButton(text)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            btn.setToolTip(tooltip)
            buttons_row.addWidget(btn)
            
            # Guardar referencia a los botones importantes
            if text == "Subir Archivo":
                self.btn_upload = btn
            elif text == "Descargar Archivo":
                self.btn_download = btn
            elif text == "Eliminar Archivo":
                self.btn_delete = btn
            elif text == "Info del Archivo":
                self.btn_info = btn
            elif text == "Tabla de Bloques":
                self.btn_block_table = btn
            elif text == "Refrescar Lista":
                self.btn_refresh = btn
        
        buttons_row.addStretch()
        main_layout.addLayout(buttons_row)
        
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
        self.files_list.doubleClicked.connect(self.main_window.on_file_double_click)
        
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
