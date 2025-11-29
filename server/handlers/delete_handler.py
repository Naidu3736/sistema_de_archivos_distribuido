import os
import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class DeleteHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa una solicitud de eliminación de archivo en nodos distribuidos"""
        try:
            # Fase 1: Verificación de existencia
            filename = NetworkUtils.receive_filename(client)
            with self.server.file_table_lock:
                file_info = self.server.file_table.get_info_file(filename)
                
            if not file_info:
                NetworkUtils.send_response(client, Response.FILE_NOT_FOUND)
                return

            # Fase 2: Eliminación distribuida
            success = self._delete_file_distributed(filename, file_info)
            
            if success:
                NetworkUtils.send_response(client, Response.DELETE_COMPLETE)
                logger.log("DELETE", f"Archivo eliminado distribuido: {filename}")
            else:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
                logger.log("DELETE", f"Error eliminando archivo distribuido: {filename}")

        except Exception as e:
            logger.log("DELETE", f'Error durante eliminación distribuida: {str(e)}')
            NetworkUtils.send_response(client, Response.SERVER_ERROR)

    def _delete_file_distributed(self, filename: str, file_info) -> bool:
        """Elimina completamente un archivo del sistema distribuido"""
        file_id = self.server.file_table.name_to_id[filename]

        try:
            # Obtener cadena de bloques
            with self.server.block_table_lock:
                block_chain = self.server.block_table.get_block_chain(file_info.first_block_id)
            
            # Eliminar bloques físicos de los nodos
            delete_success = self._delete_blocks_from_nodes(block_chain, filename, file_info.total_size)
            
            if not delete_success:
                logger.log("DELETE", f"Algunos bloques no pudieron eliminarse de los nodos: {filename}")
                # Continuamos con la eliminación lógica aunque algunos nodos fallen

            # Liberar bloques lógicos
            with self.server.block_table_lock:
                blocks_freed = self.server.block_table.free_blocks_chain(file_info.first_block_id)
            
            # Liberar espacio en nodos
            if block_chain:
                self.server.free_blocks_from_nodes(block_chain, file_info.total_size)

            # Eliminar de FileTable
            with self.server.file_table_lock:
                self.server.file_table.delete_file(file_id)

            logger.log("DELETE", f"Archivo eliminado: {filename} (bloques liberados: {blocks_freed})")
            return True
            
        except Exception as e:
            logger.log("DELETE", f"Error en eliminación distribuida: {e}")
            return False

    def _delete_blocks_from_nodes(self, block_chain: list, filename: str, file_size: int) -> bool:
        """Elimina bloques físicos de todos los nodos"""
        if not block_chain:
            return True
        
        overall_success = True
        
        for logical_id, physical_number, primary_node, replica_nodes in block_chain:
            # Eliminar del nodo primario
            if primary_node:
                primary_success = self._delete_block_from_node(primary_node, filename, logical_id, physical_number)
                if not primary_success:
                    logger.log("DELETE", f"Error eliminando bloque {logical_id} del nodo primario {primary_node}")
                    overall_success = False
            
            # Eliminar de nodos réplica
            for replica_node in replica_nodes:
                if replica_node:
                    replica_success = self._delete_block_from_node(replica_node, filename, logical_id, physical_number, is_replica=True)
                    if not replica_success:
                        logger.log("DELETE", f"Error eliminando bloque {logical_id} del nodo réplica {replica_node}")
                        # No marcamos overall_success como False para réplicas
        
        return overall_success

    def _delete_block_from_node(self, node_id: str, filename: str, logical_id: int, 
                               physical_number: int, is_replica: bool = False) -> bool:
        """Elimina un bloque específico de un nodo"""
        node_info = self.server.node_manager.get_node_info(node_id)
        if not node_info:
            logger.log("DELETE", f"Nodo no encontrado: {node_id}")
            return False
        
        # Verificar si el nodo está activo
        if not self.server.node_client.ping(node_info['host'], node_info['port']):
            logger.log("DELETE", f"Nodo inactivo, no se puede eliminar bloque: {node_id}")
            return False
        
        block_info = {
            'block_id': logical_id,
            'filename': filename,
            'physical_number': physical_number,
            'is_replica': is_replica
        }
        
        try:
            success = self.server.node_client.delete_block(
                node_info['host'], 
                node_info['port'], 
                block_info
            )
            
            if success:
                node_type = "réplica" if is_replica else "primario"
                logger.log("DELETE", f"Bloque {logical_id} eliminado de {node_type}: {node_id}")
            else:
                logger.log("DELETE", f"Error eliminando bloque {logical_id} de {node_id}")
            
            return success
            
        except Exception as e:
            logger.log("DELETE", f"Excepción eliminando bloque de {node_id}: {e}")
            return False