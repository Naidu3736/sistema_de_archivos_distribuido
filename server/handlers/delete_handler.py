import os
import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class DeleteHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa eliminación de archivo - versión optimizada"""
        try:
            filename = NetworkUtils.receive_filename(client)
            
            with self.server.file_table_lock:
                file_info = self.server.file_table.get_info_file(filename)
                
            if not file_info:
                NetworkUtils.send_response(client, Response.FILE_NOT_FOUND)
                return

            # Eliminar el archivo completo
            success = self._delete_file(filename, file_info)
            
            if success:
                NetworkUtils.send_response(client, Response.DELETE_COMPLETE)
                logger.log("DELETE", f"Archivo eliminado: {filename}")
            else:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)

        except Exception as e:
            logger.log("DELETE", f'Error eliminando archivo: {str(e)}')
            NetworkUtils.send_response(client, Response.SERVER_ERROR)

    def _delete_file(self, filename: str, file_info) -> bool:
        """Elimina completamente un archivo - versión optimizada"""
        file_id = self.server.file_table.name_to_id[filename]

        try:
            # 1. Obtener cadena de bloques
            with self.server.block_table_lock:
                block_chain = self.server.block_table.get_block_chain(file_info.first_block_id)
            
            # 2. Obtener todos los nodos únicos que contienen bloques de este archivo
            unique_nodes = self._get_unique_nodes(block_chain)
            
            # 3. Eliminar bloques físicos de nodos (por nodo)
            delete_ok = self._delete_blocks_by_node(unique_nodes, filename)
            
            # 4. Liberar espacio en coordinador
            if block_chain:
                self.server.node_manager.free_file_space(block_chain, file_info.total_size)
            
            # 5. Limpiar metadatos
            self._cleanup_metadata(file_id, filename, file_info.first_block_id)
            
            logger.log("DELETE", f"Eliminación completada: {filename} - {len(block_chain)} bloques en {len(unique_nodes)} nodos")
            return True
            
        except Exception as e:
            logger.log("DELETE", f"Error en eliminación: {e}")
            return False

    def _get_unique_nodes(self, block_chain: list) -> set:
        """Obtiene todos los nodos únicos que contienen bloques del archivo"""
        unique_nodes = set()
        
        if not block_chain:
            return unique_nodes
            
        for logical_id, physical_number, primary_node, replica_nodes in block_chain:
            if primary_node:
                unique_nodes.add(primary_node)
            for replica_node in replica_nodes:
                if replica_node:
                    unique_nodes.add(replica_node)
        
        logger.log("DELETE", f"Nodos únicos encontrados: {list(unique_nodes)}")
        return unique_nodes

    def _delete_blocks_by_node(self, unique_nodes: set, filename: str) -> bool:
        """Elimina todos los bloques de un archivo por nodo"""
        if not unique_nodes:
            return True
            
        all_ok = True
        
        for node_id in unique_nodes:
            node_info = self.server.node_manager.get_node_info(node_id)
            if not node_info:
                logger.log("DELETE", f"Nodo no encontrado: {node_id}")
                all_ok = False
                continue
                
            # Verificar si el nodo está activo
            if not self.server.node_client.ping(node_info['host'], node_info['port']):
                logger.log("DELETE", f"Nodo inactivo: {node_id}")
                all_ok = False
                continue
            
            try:
                # Usar el método delete_blocks que elimina todos los bloques del archivo
                success = self.server.node_client.delete_blocks(
                    node_info['host'], 
                    node_info['port'], 
                    filename
                )
                
                if success:
                    logger.log("DELETE", f"Todos los bloques de '{filename}' eliminados de {node_id}")
                else:
                    logger.log("DELETE", f"Error eliminando bloques de '{filename}' de {node_id}")
                    all_ok = False
                    
            except Exception as e:
                logger.log("DELETE", f"Excepción eliminando bloques de {node_id}: {e}")
                all_ok = False
        
        return all_ok

    def _cleanup_metadata(self, file_id: int, filename: str, first_block_id: int):
        """Limpia metadatos"""
        try:
            # Liberar bloques lógicos
            with self.server.block_table_lock:
                blocks_freed = self.server.block_table.free_blocks_chain(first_block_id)
            
            # Eliminar de FileTable
            with self.server.file_table_lock:
                self.server.file_table.delete_file(file_id)
                
            logger.log("DELETE", f"Metadatos limpiados: {filename} (bloques liberados: {blocks_freed})")
                
        except Exception as e:
            logger.log("DELETE", f"Error limpiando metadatos: {e}")