# Main.py (o sadtf_main_app.py)

import sys
import os
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QPushButton, QLabel, 
                             QMessageBox, QFileDialog, QTextEdit, QDialog)
# --- IMPORTACIONES CORREGIDAS ---
from PyQt5.QtCore import QCoreApplication, Qt, QThread, pyqtSignal

# Importar todos los componentes de nuestros otros archivos
from Config import NODOS_CONOCIDOS
from Utils import MetadataManager, particionar_archivo, combinar_bloques
from Network import DFSServerThread, DFSClient

# --- 1. NUEVA CLASE: Hilo de Descarga ---
# Esta clase moverá el trabajo de red fuera del hilo de la GUI
class DownloadThread(QThread):
    """
    Este hilo se encarga de todo el proceso de descarga,
    evitando que la GUI se congele.
    """
    # Señales que el hilo enviará de vuelta a la GUI
    finished = pyqtSignal(str) # (ruta_guardado) -> Éxito
    error = pyqtSignal(str)    # (mensaje_error) -> Fallo
    log = pyqtSignal(str)      # (mensaje_log) -> Actualizar log

    def __init__(self, dfs_client, bloques_info, save_path, temp_dir):
        super().__init__()
        self.dfs_client = dfs_client
        self.bloques_info = bloques_info
        self.save_path = save_path
        self.temp_dir = temp_dir
        self.rutas_bloques_descargados = []

    def run(self):
        """Este es el código que se ejecuta en el hilo separado."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir)
            
            # 2. y 3. Solicitar bloques (con tolerancia a fallas)
            for nombre_bloque, addr_original_list, addr_copia_list in self.bloques_info:
                
                addr_original = tuple(addr_original_list)
                addr_copia = tuple(addr_copia_list)

                self.log.emit(f"Solicitando {nombre_bloque} de {addr_original}...")
                # --- LLAMADA DE RED (AHORA SEGURA EN UN HILO) ---
                block_data = self.dfs_client.request_block(addr_original, nombre_bloque)
                
                if block_data is None:
                    self.log.emit(f"¡Fallo! Intentando con copia de {addr_copia}...")
                    # --- LLAMADA DE RED (AHORA SEGURA EN UN HILO) ---
                    block_data = self.dfs_client.request_block(addr_copia, nombre_bloque)
                    
                    if block_data is None:
                        # Emitir señal de error y detener
                        raise Exception(f"No se pudo recuperar el bloque {nombre_bloque} ni su copia. La descarga ha fallado.")
                
                # Guardar bloque temporalmente
                temp_path = os.path.join(self.temp_dir, nombre_bloque)
                with open(temp_path, 'wb') as f:
                    f.write(block_data)
                self.rutas_bloques_descargados.append(temp_path)

            # 4. Reconstruir (Combinar)
            self.log.emit("Combinando bloques...")
            if not combinar_bloques(self.rutas_bloques_descargados, self.save_path):
                raise Exception("No se pudo reconstruir el archivo final.")
            
            # 5. Éxito: Emitir señal de finalizado
            self.finished.emit(self.save_path)

        except Exception as e:
            # 6. Fallo: Emitir señal de error
            self.error.emit(str(e))
        
        finally:
            # Limpiar temporales
            if os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    self.log.emit("Limpieza de temporales completada.")
                except Exception as e:
                    self.log.emit(f"Error al limpiar temporales: {e}")

# --- 2. CLASE PRINCIPAL MODIFICADA ---

class SADTFMainWindow(QMainWindow):
    def __init__(self, host_ip, port):
        super().__init__()
        
        self.host_addr = (host_ip, port)
        nodo_id = f"nodo_{port}"
        
        self.setWindowTitle(f"SADTF (Nodo: {host_ip}:{port})")
        self.setGeometry(100, 100, 800, 500)
        
        self.metadata_manager = MetadataManager(nodo_id, host_ip, port)
        self.dfs_client = DFSClient()

        self.server_thread = DFSServerThread(host_ip, port, self.metadata_manager)
        self.server_thread.metadata_changed.connect(self.refresh_file_list)
        self.server_thread.log_message.connect(self.update_log)
        self.server_thread.start()
        
        self.temp_dir = f"temp_{port}"
        self.setup_ui()
        
        # Esta variable guardará la referencia al hilo trabajador
        self.download_worker = None
        
        self.refresh_file_list()

    def setup_ui(self):
        # ... (Tu código setup_ui no cambia) ...
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        title_label = QLabel("Sistema de Almacenamiento Distribuido Tipo FTP (SADTF)") # Título mejorado
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; background-color: #3f729b; color: white; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("font-family: 'Courier New', monospace; font-size: 14px;")
        main_layout.addWidget(self.file_list)
        button_layout = QHBoxLayout()
        self.btn_cargar = QPushButton("Guardar (Subir)")
        self.btn_atributos = QPushButton("Atributos de archivo")
        self.btn_tabla = QPushButton("Tabla de Bloques")
        self.btn_descargar = QPushButton("Descargar")
        self.btn_eliminar = QPushButton("Eliminar")
        button_layout.addWidget(self.btn_cargar)
        button_layout.addWidget(self.btn_atributos)
        button_layout.addWidget(self.btn_tabla)
        button_layout.addWidget(self.btn_descargar)
        button_layout.addWidget(self.btn_eliminar)
        main_layout.addLayout(button_layout)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(100)
        main_layout.addWidget(self.log_box)
        self.btn_cargar.clicked.connect(self.guardar_archivo)
        self.btn_atributos.clicked.connect(self.mostrar_atributos)
        self.btn_tabla.clicked.connect(self.mostrar_tabla_bloques)
        self.btn_descargar.clicked.connect(self.descargar_archivo)
        self.btn_eliminar.clicked.connect(self.eliminar_archivo)
        
    def update_log(self, message):
        self.log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def refresh_file_list(self):
        self.file_list.clear()
        archivos = self.metadata_manager.get_lista_archivos_formateada()
        if not archivos:
            self.file_list.addItem("...Sistema vacío...")
        else:
            self.file_list.addItems(archivos)

    def _get_selected_filename(self):
        item_seleccionado = self.file_list.currentItem()
        if not item_seleccionado:
            QMessageBox.warning(self, "Error", "Por favor, selecciona un archivo de la lista.")
            return None
        text_completo = item_seleccionado.text()
        partes = text_completo.split()
        if len(partes) < 4: return None
        nombre_archivo = " ".join(partes[:-3])
        return nombre_archivo.strip()

    def broadcast_updates(self):
        metadata_json = self.metadata_manager.get_file_table_json()
        # TODO: Mover 'guardar' y 'eliminar' a hilos
        self.dfs_client.broadcast_metadata_update(metadata_json, self.host_addr)
        self.refresh_file_list()

    # --- FUNCIÓN 'guardar_archivo' (SIN CAMBIOS POR AHORA) ---
    # NOTA: Esta función también debería moverse a un hilo.
    def guardar_archivo(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo para subir")
        if not filepath: return
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        self.update_log(f"Iniciando subida de: {filename}")
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)
        bloques = particionar_archivo(filepath, self.temp_dir)
        if not bloques:
            QMessageBox.critical(self, "Error", "No se pudo particionar el archivo.")
            return
        block_map = []
        for nombre_bloque, ruta_bloque in bloques:
            nodos_asignados = self.metadata_manager.get_nodos_para_bloque(n=2)
            if not nodos_asignados:
                self.update_log("Error: No hay nodos en la configuración.")
                continue
            
            addr_original = tuple(nodos_asignados[0])
            addr_copia = tuple(nodos_asignados[1]) if len(nodos_asignados) > 1 else addr_original
            
            if not self.dfs_client.send_block(addr_original, nombre_bloque, ruta_bloque):
                self.update_log(f"Fallo al enviar bloque {nombre_bloque} a {addr_original}")
            if not self.dfs_client.send_block(addr_copia, nombre_bloque, ruta_bloque):
                self.update_log(f"Fallo al enviar copia de {nombre_bloque} a {addr_copia}")
            block_map.append((nombre_bloque, addr_original, addr_copia))
            
        self.metadata_manager.add_file_entry(filename, file_size, block_map)
        self.broadcast_updates()
        shutil.rmtree(self.temp_dir)
        self.update_log(f"¡Subida de {filename} completada!")
        QMessageBox.information(self, "Éxito", f"'{filename}' ha sido subido al sistema.")

    # --- FUNCIÓN 'descargar_archivo' (AHORA USA HILOS) ---
    def descargar_archivo(self):
        """
        Inicia el proceso de descarga en un hilo separado.
        """
        filename = self._get_selected_filename()
        if not filename:
            return

        bloques_info = self.metadata_manager.get_file_blocks(filename)
        if not bloques_info:
            QMessageBox.critical(self, "Error", "No se encontró información de bloques para este archivo.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo como...", filename)
        if not save_path:
            return

        self.update_log(f"Iniciando descarga de: {filename}...")
        
        # 1. Crear el hilo
        self.download_worker = DownloadThread(
            dfs_client=self.dfs_client,
            bloques_info=bloques_info,
            save_path=save_path,
            temp_dir=self.temp_dir
        )
        
        # 2. Conectar las señales del hilo a las funciones de la GUI
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.log.connect(self.update_log)
        
        # 3. Deshabilitar botones para evitar clics múltiples
        self.btn_descargar.setEnabled(False)
        self.btn_cargar.setEnabled(False)
        self.btn_eliminar.setEnabled(False)

        # 4. Iniciar el hilo
        self.download_worker.start()

    # --- NUEVAS FUNCIONES (Manejadores de Señales) ---
    def on_download_finished(self, save_path):
        """Se llama cuando el hilo de descarga termina con éxito."""
        self.update_log(f"Descarga completada: {save_path}")
        QMessageBox.information(self, "Éxito", f"Archivo descargado y reconstruido en:\n{save_path}")
        self.re_enable_buttons()

    def on_download_error(self, error_message):
        """Se llama cuando el hilo de descarga falla."""
        self.update_log(f"ERROR CRÍTICO en descarga: {error_message}")
        QMessageBox.critical(self, "Error de Descarga", f"Falló la descarga:\n{error_message}")
        self.re_enable_buttons()

    def re_enable_buttons(self):
        """Reactiva los botones de la GUI."""
        self.btn_descargar.setEnabled(True)
        self.btn_cargar.setEnabled(True)
        self.btn_eliminar.setEnabled(True)

    # --- FUNCIÓN 'eliminar_archivo' (AÚN SIN HILOS) ---
    # NOTA: Esta función también debería moverse a un hilo
    def eliminar_archivo(self):
        filename = self._get_selected_filename()
        if not filename:
            return
        try:
            confirm = QMessageBox.question(self, "Confirmar Eliminación", 
                                          f"¿Estás seguro de que quieres eliminar '{filename}' de forma permanente?",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if confirm == QMessageBox.No:
                return
            bloques_a_eliminar = self.metadata_manager.remove_file_entry(filename)
            if not bloques_a_eliminar:
                QMessageBox.critical(self, "Error", "El archivo ya no existe en los metadatos.")
                self.broadcast_updates()
                return
            self.update_log(f"Iniciando eliminación de: {filename}")
            for nombre_bloque, addr_original_list, addr_copia_list in bloques_a_eliminar:
                addr_original = tuple(addr_original_list)
                addr_copia = tuple(addr_copia_list)
                if not self.dfs_client.send_delete_block(addr_original, nombre_bloque):
                    self.update_log(f"Fallo al contactar {addr_original} para eliminar {nombre_bloque}")
                if (addr_original != addr_copia) and (not self.dfs_client.send_delete_block(addr_copia, nombre_bloque)):
                    self.update_log(f"Fallo al contactar {addr_copia} para eliminar copia de {nombre_bloque}")
            self.broadcast_updates()
            self.update_log(f"Eliminación de {filename} completada.")
            QMessageBox.information(self, "Éxito", f"'{filename}' ha sido eliminado del sistema.")
        except Exception as e:
            self.update_log(f"ERROR CRÍTICO en eliminación: {e}")
            QMessageBox.critical(self, "Error de Eliminación", f"Falló la eliminación:\n{e}")

    # --- OTRAS FUNCIONES (SIN CAMBIOS) ---
    def mostrar_atributos(self):
        filename = self._get_selected_filename()
        if not filename: return
        info = self.metadata_manager.get_file_attributes(filename)
        self.show_text_dialog("Atributos de Archivo", info)

    def mostrar_tabla_bloques(self):
        info = self.metadata_manager.get_block_table_content()
        self.show_text_dialog("Contenido de la Tabla de Bloques", info)

    def show_text_dialog(self, title, text):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setText(text)
        text_widget.setStyleSheet("font-family: 'Courier New', monospace;")
        layout.addWidget(text_widget)
        dialog.setLayout(layout)
        dialog.exec_()

    def closeEvent(self, event):
        self.update_log("Cerrando el nodo...")
        self.server_thread.stop()
        self.server_thread.wait()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        event.accept()

# --- Arranque de la Aplicación (Corregido para IPs de LAN) ---
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Error: Debes especificar el puerto del nodo.")
        print(f"Uso: python {sys.argv[0]} <puerto>")
        print("Puertos válidos en config:", [addr[1] for addr in NODOS_CONOCIDOS.values()])
        sys.exit(1)
        
    try:
        PORT = int(sys.argv[1])
        NODE_IP = None
        for ip, port_val in NODOS_CONOCIDOS.values():
            if port_val == PORT:
                NODE_IP = ip
                break
        if NODE_IP is None:
            raise ValueError(f"Puerto {PORT} no encontrado en NODOS_CONOCIDOS")
    except ValueError as e:
        print(f"Error: Puerto '{sys.argv[1]}' no es válido o no está en sadtf_config.py")
        print(e)
        sys.exit(1)
    
    app = QApplication(sys.argv)
    print(f"Iniciando Nodo en: {NODE_IP}:{PORT}")
    main_window = SADTFMainWindow(NODE_IP, PORT) 
    main_window.show()
    sys.exit(app.exec_())