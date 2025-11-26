import os
import json
from datetime import datetime

class FileTable:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.files = {}
        self.name_to_id = {}
        self.next_file_id = 0
        
        # Cargar datos existentes
        self._load_from_disk()

    def _load_from_disk(self):
        """Carga la tabla desde disco"""
        file_table_path = os.path.join(self.data_dir, "file_table.json")
        if os.path.exists(file_table_path):
            try:
                with open(file_table_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.files = {int(k): v for k, v in data['files'].items()}
                    self.name_to_id = data['name_to_id']
                    self.next_file_id = data['next_file_id']
                
                # Convertir strings de fecha a objetos datetime
                for file_id, file_info in self.files.items():
                    if isinstance(file_info['created_at'], str):
                        file_info['created_at'] = datetime.fromisoformat(file_info['created_at'])
                
                print(f"FileTable cargada desde disco - {len(self.files)} archivos registrados")
            except Exception as e:
                print(f"Error cargando FileTable: {e}. Inicializando nueva tabla.")
                self._initialize_empty()
        else:
            self._initialize_empty()
            print("FileTable inicializada nueva")

    def _save_to_disk(self):
        """Guarda la tabla en disco"""
        file_table_path = os.path.join(self.data_dir, "file_table.json")
        try:
            # Convertir datetime a string para JSON
            files_serializable = {}
            for file_id, file_info in self.files.items():
                files_serializable[file_id] = file_info.copy()
                files_serializable[file_id]['created_at'] = file_info['created_at'].isoformat()
            
            data = {
                'files': files_serializable,
                'name_to_id': self.name_to_id,
                'next_file_id': self.next_file_id
            }
            
            with open(file_table_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando FileTable: {e}")

    def _initialize_empty(self):
        """Inicializa una tabla vacía"""
        self.files = {}
        self.name_to_id = {}
        self.next_file_id = 0

    def create_file(self, filename: str, total_size: int) -> int:
        file_id = self.next_file_id

        self.files[file_id] = {
            "filename": filename,
            "total_size": total_size,
            "created_at": datetime.now(),
            "first_block_id": None,
            "block_count": 0
        }

        self.name_to_id[filename] = file_id
        self.next_file_id += 1

        self._save_to_disk()  # Persistir cambios
        return file_id
    
    def set_first_block(self, file_id: int, first_block_id: int):
        if file_id in self.files:
            self.files[file_id]["first_block_id"] = first_block_id
            self._save_to_disk()  # Persistir cambios

    def update_block_count(self, file_id: int, block_count: int):
        if file_id in self.files:
            self.files[file_id]["block_count"] = block_count
            self._save_to_disk()  # Persistir cambios

    def delete_file(self, file_id: int):
        """Elimina un archivo de la tabla"""
        if file_id in self.files:
            filename = self.files[file_id]["filename"]
            del self.files[file_id]
            if filename in self.name_to_id:
                del self.name_to_id[filename]
            self._save_to_disk()  # Persistir cambios

    def get_info_file(self, filename: str):
        file_id = self.name_to_id.get(filename)
        return self.files.get(file_id) if file_id is not None else None