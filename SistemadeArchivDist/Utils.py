# sadtf_utils.py

import os
import shutil
import json
import random
from datetime import datetime
from Config import BLOCK_SIZE, NODOS_CONOCIDOS, LOCAL_STORAGE_DIR

# --- 1. Lógica de Partición y Combinación ---
def particionar_archivo(archivo_entrada, directorio_salida_temp):
    if not os.path.exists(directorio_salida_temp):
        os.makedirs(directorio_salida_temp)

    bloques_creados = []
    nombre_base = os.path.basename(archivo_entrada)
    
    try:
        with open(archivo_entrada, 'rb') as f_entrada:
            parte_actual = 1
            while True:
                buffer = f_entrada.read(BLOCK_SIZE)
                if not buffer:
                    break
                
                nombre_bloque = f"{nombre_base}_b{parte_actual}.bin"
                ruta_bloque = os.path.join(directorio_salida_temp, nombre_bloque)
                
                with open(ruta_bloque, 'wb') as f_salida:
                    f_salida.write(buffer)
                
                bloques_creados.append((nombre_bloque, ruta_bloque))
                parte_actual += 1
        
        return bloques_creados
        
    except IOError as e:
        print(f"Error al particionar archivo: {e}")
        return []

def combinar_bloques(bloques_temp, archivo_salida):
    try:
        with open(archivo_salida, 'wb') as f_salida:
            for ruta_bloque in bloques_temp:
                with open(ruta_bloque, 'rb') as f_entrada:
                    shutil.copyfileobj(f_entrada, f_salida)
        return True
    except IOError as e:
        print(f"Error al combinar bloques: {e}")
        return False
    

def combinar_bloques(bloques_temp, archivo_salida):
    """
    Combina una lista de bloques (leídos desde archivos temporales) en un archivo de salida.
    """
    try:
        with open(archivo_salida, 'wb') as f_salida:
            for ruta_bloque in bloques_temp:
                with open(ruta_bloque, 'rb') as f_entrada:
                    shutil.copyfileobj(f_entrada, f_salida)
        return True
    except IOError as e:
        print(f"Error al combinar bloques: {e}")
        return False

# --- 2. Lógica de Metadatos (Tabla de Bloques) ---

class MetadataManager:
    """
    Gestiona la 'Tabla de Bloques' (en este caso, un 'file_table').
    Esta clase es la responsable de mantener el estado del sistema sincronizado.
    """
    def __init__(self, nodo_id, host_ip, port):
        self.nodo_id = nodo_id
        self.host_addr = (host_ip, port)
        
        self.storage_dir = f"{LOCAL_STORAGE_DIR}_{port}"
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        self.file_table = {}

    def get_lista_archivos_formateada(self):
        lista = []
        for nombre, data in self.file_table.items():
            kb_size = data['size'] / 1024
            fecha_str = data.get('date', 'N/A')
            lista.append(f"{nombre:<30} {fecha_str:<15} {kb_size:,.0f} KB")
        return lista

    def add_file_entry(self, nombre_original, size, block_map):
        self.file_table[nombre_original] = {
            'size': size,
            'date': datetime.now().strftime("%d/%m/%Y"),
            'blocks': block_map
        }
        
    def remove_file_entry(self, nombre_original):
        if nombre_original in self.file_table:
            entry = self.file_table.pop(nombre_original)
            return entry['blocks']
        return []

    def get_file_blocks(self, nombre_original):
        return self.file_table.get(nombre_original, {}).get('blocks', [])

    def get_file_attributes(self, nombre_original):
        if nombre_original not in self.file_table:
            return "Archivo no encontrado."
            
        data = self.file_table[nombre_original]
        info = f"Atributos de: {nombre_original}\n"
        info += f"Tamaño: {data['size'] / 1024:,.0f} KB\n"
        info += "Ubicación de Bloques:\n"
        
        for i, (nombre_bloque, original_addr, copia_addr) in enumerate(data['blocks']):
            info += f"  - Bloque {i+1} ({nombre_bloque}):\n"
            info += f"    - Original: {original_addr[0]}:{original_addr[1]}\n"
            info += f"    - Copia:    {copia_addr[0]}:{copia_addr[1]}\n"
        return info

    def get_block_table_content(self):
        if not self.file_table:
            return "La Tabla de Bloques está vacía."
            
        info = "=== TABLA de BLOQUES (Vista de Archivos) ===\n"
        for nombre_archivo, data in self.file_table.items():
            info += f"\nArchivo: {nombre_archivo}\n"
            for nombre_bloque, original, copia in data['blocks']:
                # Mostramos solo el puerto para que sea más legible
                info += f"  -> {nombre_bloque} @ ({original[1]}, {copia[1]})\n"
        return info

    def get_nodos_para_bloque(self, n=2):
        """
        *** FUNCIÓN CORREGIDA ***
        Selecciona 'n' nodos aleatorios de la lista COMPLETA.
        """
        
        # 1. Obtener la lista COMPLETA de nodos, incluyéndonos.
        lista_nodos = list(NODOS_CONOCIDOS.values())
        
        if not lista_nodos:
            # No hay nodos definidos
            return []
            
        # 2. Caso borde: Si pedimos 2 nodos pero solo hay 1 (o menos)
        if len(lista_nodos) < n:
            # Devolvemos el único nodo que existe, duplicado.
            return [lista_nodos[0]] * n
            
        # 3. Seleccionar 'n' nodos DIFERENTES aleatoriamente
        #    de la lista completa.
        #    random.sample() garantiza que no se repitan (sin reemplazo).
        return random.sample(lista_nodos, n)

    def set_file_table(self, new_table_json):
        try:
            self.file_table = json.loads(new_table_json)
            return True
        except json.JSONDecodeError:
            return False

    def get_file_table_json(self):
        return json.dumps(self.file_table)

    def get_local_storage_path(self, nombre_bloque):
        return os.path.join(self.storage_dir, nombre_bloque)