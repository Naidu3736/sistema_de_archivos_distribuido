from dataclasses import dataclass, field, asdict
import os
import json
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class FileEntry:
    filename: str
    total_size: int
    created_at: datetime = field(default_factory=datetime.now)
    first_block_id: Optional[int] = None
    block_count: int = 0

    def to_dict(self):
        d = asdict(self)
        # asegurar serializable JSON
        d['created_at'] = self.created_at.isoformat()
        return d

    @staticmethod
    def from_dict(data: dict) -> "FileEntry":
        created = data.get('created_at')
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        return FileEntry(
            filename=data['filename'],
            total_size=data['total_size'],
            created_at=created,
            first_block_id=data.get('first_block_id'),
            block_count=data.get('block_count', 0)
        )

    def __getitem__(self, key):
        if key == 'created_at':
            return self.created_at.isoformat()
        if key in ('filename', 'total_size', 'first_block_id', 'block_count'):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key == 'created_at':
            if isinstance(value, str):
                self.created_at = datetime.fromisoformat(value)
            elif isinstance(value, datetime):
                self.created_at = value
            else:
                raise TypeError("created_at must be datetime or ISO string")
            return
        if key in ('filename', 'total_size', 'first_block_id', 'block_count'):
            setattr(self, key, value)
            return
        raise KeyError(key)


class FileTable:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # ahora almacenamos FileEntry en lugar de dicts
        self.files: Dict[int, FileEntry] = {}
        self.name_to_id: Dict[str, int] = {}
        self.next_file_id = 0
        
        # Cargar datos existentes
        self._load_from_disk()
        
        if not self.files:
            self._save_to_disk()

    def _load_from_disk(self):
        """Carga la tabla desde disco"""
        file_table_path = os.path.join(self.data_dir, "file_table.json")
        if os.path.exists(file_table_path):
            try:
                with open(file_table_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Reconstruir FileEntry desde dicts
                    self.files = {int(k): FileEntry.from_dict(v) for k, v in data.get('files', {}).items()}
                    # Asegurar que name_to_id tenga valores enteros
                    name_to_id_raw = data.get('name_to_id', {})
                    if isinstance(name_to_id_raw, dict):
                        self.name_to_id = {k: int(v) for k, v in name_to_id_raw.items()}
                    else:
                        self.name_to_id = {}
                    self.next_file_id = int(data.get('next_file_id', 0))
                
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
            # Convertir FileEntry a dict serializable
            files_serializable = {}
            for file_id, file_entry in self.files.items():
                files_serializable[str(file_id)] = file_entry.to_dict()
            
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
        # Evitar duplicados: si ya existe, devolver id existente
        if filename in self.name_to_id:
            existing_id = self.name_to_id[filename]
            print(f"create_file: '{filename}' ya existe con id {existing_id}")
            return existing_id

        if total_size < 0:
            raise ValueError("total_size must be >= 0")

        file_id = self.next_file_id

        # Crear FileEntry
        self.files[file_id] = FileEntry(
            filename=filename,
            total_size=total_size
        )

        self.name_to_id[filename] = file_id
        self.next_file_id += 1

        self._save_to_disk()  # Persistir cambios
        return file_id
    
    def set_first_block(self, file_id: int, first_block_id: int):
        if file_id in self.files:
            self.files[file_id].first_block_id = first_block_id
            self._save_to_disk()  # Persistir cambios

    def update_block_count(self, file_id: int, block_count: int):
        if file_id in self.files:
            self.files[file_id].block_count = block_count
            self._save_to_disk()  # Persistir cambios

    def delete_file(self, file_id: int):
        """Elimina un archivo de la tabla"""
        if file_id in self.files:
            filename = self.files[file_id].filename
            del self.files[file_id]
            if filename in self.name_to_id:
                del self.name_to_id[filename]
            self._save_to_disk()  # Persistir cambios

    def get_info_file(self, filename: str):
        file_id = self.name_to_id.get(filename)
        # Devolver la entrada FileEntry (o None). El consumidor puede acceder a atributos.
        return self.files.get(file_id) if file_id is not None else None

    def get_file_by_id(self, file_id: int) -> Optional[FileEntry]:
        """Obtener FileEntry por id"""
        return self.files.get(file_id)

    def rename_file(self, file_id: int, new_name: str) -> bool:
        """Renombrar un archivo; devuelve True si se renombró"""
        if file_id not in self.files:
            return False
        if new_name in self.name_to_id and self.name_to_id[new_name] != file_id:
            # nombre ya en uso por otro id
            return False
        old_name = self.files[file_id].filename
        # actualizar estructuras
        self.files[file_id].filename = new_name
        if old_name in self.name_to_id:
            del self.name_to_id[old_name]
        self.name_to_id[new_name] = file_id
        self._save_to_disk()
        return True

    def get_all_files(self) -> List[dict]:
        """Obtiene información de todos los archivos (para listado)"""
        files_list = [
            {
                'id': file_id,
                'filename': info.filename,
                'size': info.total_size,
                'created_at': info.created_at.isoformat(),
                'block_count': info.block_count
            }
            for file_id, info in self.files.items()
        ]
        # ordenar por nombre para salida consistente
        return sorted(files_list, key=lambda x: x['filename'])
    
    def file_exists(self, filename: str) -> bool:
        """Verifica si un archivo ya existe en el sistema por nombre"""
        return filename in self.name_to_id