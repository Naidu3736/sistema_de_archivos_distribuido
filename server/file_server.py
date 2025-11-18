import os
import socket
import shutil
import json
from core.split_union import split
from core.protocol import Response
from block_table import BlockTable
from file_table import FileTable

class FileServer:
    def __init__(self, capacity_mb: int = 1000, block_dir: str = "blocks", temp_dir: str = "temp", 
                 buffer_size: int = 4096, data_dir: str = "data"):
        self.capacity_mb = capacity_mb
        self.block_dir = block_dir
        self.temp_dir = temp_dir
        self.data_dir = data_dir
        self.BUFFER_SIZE = buffer_size
        
        # Crear directorios necesarios
        os.makedirs(block_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Inicializar tablas
        total_blocks = capacity_mb
        self.block_table = BlockTable(total_blocks=total_blocks, data_dir=data_dir)
        self.file_table = FileTable(data_dir=data_dir)
        
        print(f"Servidor de archivos listo - {total_blocks} bloques disponibles")
        print(f"Archivos registrados: {len(self.file_table.files)}")

    def process_upload_request(self, client: socket.socket):
        """Procesa una solicitud de upload del cliente"""
        try:
            filename, file_size, temp_file_path = self._receive_temp_file(client)
            
            # Verificar si el archivo ya existe
            if self.file_table.get_info_file(filename):
                client.send(Response.FILE_ALREADY_EXISTS.to_bytes())
                self._cleanup_temp_file(temp_file_path)
                return None

            file_id = self.file_table.create_file(filename, file_size)
            blocks_info = self._process_file_blocks(temp_file_path, file_id)
            self._cleanup_temp_file(temp_file_path)
            
            client.send(Response.UPLOAD_COMPLETE.to_bytes())
            print(f"Upload completado - FileID: {file_id}, Bloques: {len(blocks_info['blocks'])}")
            return blocks_info
        
        except Exception as e:
            print(f"Error durante upload: {str(e)}")
            client.send(Response.SERVER_ERROR.to_bytes())
            return None

    def process_download_request(self, client: socket.socket):
        """Procesa una solicitud de download del cliente"""
        try:
            filename = self._receive_filename(client)
            file_info = self.file_table.get_info_file(filename)
            
            if not file_info:
                print(f'Archivo no encontrado: {filename}')
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return

            client.send(Response.SUCCESS.to_bytes())
            self._send_file_to_client(client, filename, file_info)
            client.send(Response.DOWNLOAD_COMPLETE.to_bytes())

        except Exception as e:
            print(f'Error durante descarga: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def process_delete_request(self, client: socket.socket):
        """Procesa una solicitud de eliminación de archivo"""
        try:
            filename = self._receive_filename(client)
            file_info = self.file_table.get_info_file(filename)
            
            if not file_info:
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return

            self._delete_file(filename, file_info)
            client.send(Response.DELETE_COMPLETE.to_bytes())
            print(f"Archivo eliminado: {filename}")

        except Exception as e:
            print(f'Error durante eliminación: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def process_list_request(self, client: socket.socket):
        """Procesa una solicitud de listado de archivos"""
        try:
            files_info = []
            for file_id, file_info in self.file_table.files.items():
                files_info.append({
                    'filename': file_info['filename'],
                    'size': file_info['total_size'],
                    'created_at': file_info['created_at'].isoformat(),
                    'blocks': file_info['block_count']
                })
            

            files_json = json.dumps(files_info).encode('utf-8')
            client.send(len(files_json).to_bytes(4, 'big'))
            client.send(files_json)
            
            print(f"Listado enviado - {len(files_info)} archivos")
            
        except Exception as e:
            print(f'Error durante listado: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def process_info_request(self, client: socket.socket):
        """Procesa solicitud de información de archivo"""
        try:
            filename = self._receive_filename(client)
            file_info = self.get_file_info(filename)
            
            if not file_info:
                client.send(Response.FILE_NOT_FOUND.to_bytes())
                return
            
            file_info_serializable = file_info.copy()
            file_info_serializable['created_at'] = file_info['created_at'].isoformat()
            
            info_json = json.dumps(file_info_serializable).encode('utf-8')
            client.send(len(info_json).to_bytes(4, 'big'))
            client.send(info_json)
            
        except Exception as e:
            print(f'Error durante info: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def process_storage_status_request(self, client: socket.socket):
        """Procesa solicitud de estado del almacenamiento"""
        try:
            status = self.get_storage_status()
            
            status_json = json.dumps(status).encode('utf-8')
            client.send(len(status_json).to_bytes(4, 'big'))
            client.send(status_json)
            
        except Exception as e:
            print(f'Error durante storage status: {str(e)}')
            client.send(Response.SERVER_ERROR.to_bytes())

    def _receive_filename(self, client: socket.socket) -> str:
        """Recibe el nombre de archivo del cliente"""
        filename_size = int.from_bytes(client.recv(4), 'big')
        filename_bytes = client.recv(filename_size)
        return filename_bytes.decode('utf-8')

    def _receive_temp_file(self, client: socket.socket):
        """Recibe el archivo completo del cliente"""
        print("Recibiendo información del archivo...")
        
        # Recibir nombre
        size_bytes = client.recv(4)
        size = int.from_bytes(size_bytes, 'big')
        file_bytes = client.recv(size)
        filename = file_bytes.decode('utf-8')

        # Recibir tamaño
        file_size_bytes = client.recv(8)
        file_size = int.from_bytes(file_size_bytes, 'big')

        print(f'Recibiendo: {filename} ({file_size} bytes)')

        # Recibir contenido
        temp_file = os.path.join(self.temp_dir, filename)
        self._receive_file_content(client, temp_file, file_size)
        
        return filename, file_size, temp_file

    def _receive_file_content(self, client: socket.socket, file_path: str, file_size: int):
        """Recibe el contenido de un archivo"""
        with open(file_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                chunk = client.recv(min(self.BUFFER_SIZE, file_size - bytes_received))
                if not chunk:
                    break
                f.write(chunk)
                bytes_received += len(chunk)

                # Mostrar progreso cada 1MB
                if bytes_received % (1024 * 1024) == 0 or bytes_received == file_size:
                    mb_received = bytes_received / (1024 * 1024)
                    mb_total = file_size / (1024 * 1024)
                    print(f"Progreso: {mb_received:.1f} / {mb_total:.1f} MB")

        print(f"Recepción completada: {os.path.basename(file_path)}")

    def _process_file_blocks(self, file_path: str, file_id: int) -> dict:
        """Procesa la división y asignación de bloques de un archivo"""
        filename = os.path.basename(file_path)
        print(f"Dividiendo archivo en bloques: {filename}")

        # Dividir archivo físicamente
        blocks_info = self._split_into_blocks(file_path)
        num_blocks = len(blocks_info['blocks'])

        # Asignar bloques lógicos
        allocated_blocks = self.block_table.allocate_blocks(file_id, num_blocks)
        self._update_file_table_blocks(file_id, allocated_blocks, num_blocks)
        
        # Renombrar bloques físicos
        self._rename_physical_blocks(blocks_info, allocated_blocks)
        
        return blocks_info

    def _split_into_blocks(self, file_path: str) -> dict:
        """Divide el archivo en bloques físicos"""
        filename = os.path.basename(file_path)
        sub_dir = os.path.splitext(filename)[0]
        sub_dir_path = os.path.join(self.block_dir, sub_dir)

        blocks = split(file_path, sub_dir_path)
        print(f'División completada: {len(blocks)} bloques creados')
        
        return {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': blocks,
            'blocks_dir': sub_dir_path
        }

    def _update_file_table_blocks(self, file_id: int, allocated_blocks: list, num_blocks: int):
        """Actualiza la información de bloques en FileTable"""
        if allocated_blocks:
            self.file_table.set_first_block(file_id, allocated_blocks[0])
            self.file_table.update_block_count(file_id, num_blocks)
            print(f"Bloques asignados: {allocated_blocks}")

    def _rename_physical_blocks(self, blocks_info: dict, allocated_blocks: list):
        """Renombra bloques físicos según IDs lógicos"""
        blocks_dir = blocks_info['blocks_dir']
        original_blocks = blocks_info['blocks']
        
        for i, block_id in enumerate(allocated_blocks):
            original_path = os.path.join(blocks_dir, original_blocks[i])
            new_name = f"block_{block_id}.bin"
            new_path = os.path.join(blocks_dir, new_name)
            
            os.rename(original_path, new_path)
            original_blocks[i] = new_name
        
        print(f"Bloques renombrados: {allocated_blocks}")

    def _send_file_to_client(self, client: socket.socket, filename: str, file_info: dict):
        """Envía un archivo al cliente"""
        block_chain = self.block_table.get_block_chain(file_info["first_block_id"])
        
        if not block_chain:
            print(f'Cadena de bloques vacía para: {filename}')
            return

        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.block_dir, sub_dir)
        
        if not os.path.exists(blocks_dir):
            print(f'Directorio de bloques no encontrado: {blocks_dir}')
            return

        blocks = [f"block_{block_id}.bin" for block_id in block_chain]
        blocks_info = {
            'sub_dir': sub_dir,
            'filename': filename,
            'blocks': blocks,
            'blocks_dir': blocks_dir
        }

        print(f"Enviando {len(blocks)} bloques...")
        self._send_blocks_to_client(client, blocks_info)
        print(f'Descarga completada: {filename}')

    def _send_blocks_to_client(self, client: socket.socket, blocks_info: dict):
        """Envía todos los bloques al cliente"""
        sub_dir_bytes = blocks_info['sub_dir'].encode('utf-8')
        client.send(len(sub_dir_bytes).to_bytes(4, 'big'))
        client.send(sub_dir_bytes)

        filename_bytes = blocks_info['filename'].encode('utf-8')
        client.send(len(filename_bytes).to_bytes(4, 'big'))
        client.send(filename_bytes)

        client.send(len(blocks_info['blocks']).to_bytes(4, 'big'))

        # Enviar nombres de bloques
        for block in blocks_info['blocks']:
            block_name_bytes = block.encode('utf-8')
            client.send(len(block_name_bytes).to_bytes(4, 'big'))
            client.send(block_name_bytes)

        # Enviar contenido de bloques
        for i, block in enumerate(blocks_info['blocks']):
            self._send_single_block(client, block, blocks_info['blocks_dir'])
            print(f"Bloque {i+1}/{len(blocks_info['blocks'])} enviado")

    def _send_single_block(self, client: socket.socket, block_name: str, blocks_dir: str):
        """Envía un solo bloque al cliente"""
        block_path = os.path.join(blocks_dir, block_name)
        
        if not os.path.exists(block_path):
            print(f"Bloque no encontrado: {block_path}")
            return

        block_size = os.path.getsize(block_path)
        client.send(block_size.to_bytes(8, 'big'))

        with open(block_path, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < block_size:
                chunk = f.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                client.send(chunk)
                bytes_sent += len(chunk)

    def _delete_file(self, filename: str, file_info: dict):
        """Elimina un archivo del sistema"""
        file_id = self.file_table.name_to_id[filename]

        # Liberar bloques lógicos
        if file_info["first_block_id"] is not None:
            blocks_freed = self.block_table.free_blocks(file_info["first_block_id"])
            print(f"Bloques liberados: {blocks_freed}")

        # Eliminar de FileTable
        self.file_table.delete_file(file_id)

        # Eliminar archivos físicos
        sub_dir = os.path.splitext(filename)[0]
        blocks_dir = os.path.join(self.block_dir, sub_dir)
        
        if os.path.exists(blocks_dir):
            shutil.rmtree(blocks_dir)
            print(f"Directorio eliminado: {blocks_dir}")

    def _cleanup_temp_file(self, temp_file_path):
        """Elimina archivo temporal"""
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"Archivo temporal eliminado: {temp_file_path}")
        except Exception as e:
            print(f"Error limpiando archivo temporal: {str(e)}")

    def get_storage_status(self):
        """Obtiene el estado del almacenamiento"""
        block_status = self.block_table.get_system_status()
        
        return {
            "total_blocks": block_status["total_blocks"],
            "used_blocks": block_status["used_blocks"],
            "free_blocks": block_status["free_blocks"],
            "usage_percent": block_status["usage_percent"],
            "file_count": len(self.file_table.files),
            "total_files_size": sum(file_info["total_size"] for file_info in self.file_table.files.values())
        }

    def get_file_info(self, filename: str):
        """Obtiene información detallada de un archivo"""
        file_info = self.file_table.get_info_file(filename)
        if not file_info:
            return None

        block_chain = []
        if file_info["first_block_id"] is not None:
            block_chain = self.block_table.get_block_chain(file_info["first_block_id"])

        return {
            "filename": file_info["filename"],
            "size": file_info["total_size"],
            "created_at": file_info["created_at"],
            "block_count": file_info["block_count"],
            "first_block_id": file_info["first_block_id"],
            "block_chain": block_chain
        }

    def cleanup(self):
        """Limpia recursos (para shutdown ordenado)"""
        print("Cerrando servidor de archivos...")
        # Las tablas ya se autoguardan automáticamente
        # Podemos forzar un guardado final si es necesario
        print("Estado guardado correctamente")