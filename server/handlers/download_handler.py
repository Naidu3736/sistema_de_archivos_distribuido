# download_handler.py (VERSIÓN CORREGIDA - SERVIDOR)
import os
import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class DownloadHandler:
    def __init__(self, file_server):
        self.server = file_server
        
    def process(self, client: socket.socket):
        """Procesa una solicitud de download del cliente"""
        try:
            # Fase 1: Verificación de existencia
            filename = NetworkUtils.receive_filename(client)
            logger.log("DOWNLOAD", f"Solicitando descarga: {filename}")
            
            with self.server.file_table_lock:
                file_info = self.server.file_table.get_info_file(filename)
                
            if not file_info:
                logger.log("DOWNLOAD", f'Archivo no encontrado: {filename}')
                NetworkUtils.send_response(client, Response.FILE_NOT_FOUND)
                return

            # Fase 2: Enviar confirmación y metadatos
            NetworkUtils.send_response(client, Response.SUCCESS)
            self._send_file_to_client(client, filename, file_info)

        except Exception as e:
            logger.log("DOWNLOAD", f'Error durante descarga: {str(e)}')
            try:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
            except:
                pass  # El cliente ya se desconectó

    def _send_file_to_client(self, client: socket.socket, filename: str, file_info):
        """Envía el archivo al cliente desde los nodos"""
        logger.log("DOWNLOAD", f"Enviando archivo: {filename} - {file_info.block_count} bloques, {file_info.total_size} bytes")
        
        try:
            # Obtener cadena de bloques
            with self.server.block_table_lock:
                block_chain = self.server.block_table.get_block_chain(file_info.first_block_id)
            
            if not block_chain:
                logger.log("DOWNLOAD", f'Cadena de bloques vacía para: {filename}')
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
                return

            # Enviar metadatos del archivo (LO QUE EL CLIENTE ESPERA)
            NetworkUtils.send_filename(client, filename)
            # El cliente espera: filename + block_count
            client.send(len(block_chain).to_bytes(4, 'big'))  # Número de bloques

            # Enviar cada bloque
            total_sent = 0
            for i, (logical_id, physical_number, primary_node, replica_nodes) in enumerate(block_chain):
                block_data = self._get_block_from_nodes(
                    logical_id, physical_number, primary_node, replica_nodes, filename
                )
                
                if block_data:
                    # Enviar tamaño del bloque y luego los datos
                    NetworkUtils.send_file_size(client, len(block_data))
                    client.send(block_data)
                    total_sent += len(block_data)
                    logger.log("DOWNLOAD", f"Bloque {i+1}/{len(block_chain)} enviado - {len(block_data)} bytes")
                else:
                    logger.log("DOWNLOAD", f"Error recuperando bloque {i}, enviando bloque vacío")
                    # Enviar bloque vacío para mantener la secuencia
                    NetworkUtils.send_file_size(client, 0)
                    # No enviamos datos para bloque de tamaño 0

            # Enviar confirmación final
            NetworkUtils.send_response(client, Response.DOWNLOAD_COMPLETE)
            logger.log("DOWNLOAD", f'Descarga completada: {filename} - {total_sent} bytes enviados')

        except (ConnectionResetError, BrokenPipeError) as e:
            logger.log("DOWNLOAD", f"Cliente cerró la conexión durante descarga: {e}")
        except Exception as e:
            logger.log("DOWNLOAD", f"Error enviando archivo: {e}")
            try:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
            except:
                pass

    def _get_block_from_nodes(self, logical_id: int, physical_number: int, 
                             primary_node: str, replica_nodes: list, filename: str) -> bytes:
        """Obtiene un bloque de los nodos (primario primero, luego réplicas)"""
        block_info = {
            'block_id': logical_id,
            'filename': filename,
            'physical_number': physical_number
        }
        
        # Intentar primero con el nodo primario
        if primary_node:
            node_info = self.server.node_manager.get_node_info(primary_node)
            if node_info and self.server.node_client.ping(node_info['host'], node_info['port']):
                try:
                    block_data = self.server.node_client.get_block(
                        node_info['host'], node_info['port'], block_info
                    )
                    if block_data:
                        return block_data
                except Exception as e:
                    logger.log("DOWNLOAD", f"Error recuperando bloque {logical_id} del primario {primary_node}: {e}")
        
        # Si el primario falla, intentar con las réplicas
        for replica_node in replica_nodes:
            if replica_node:
                node_info = self.server.node_manager.get_node_info(replica_node)
                if node_info and self.server.node_client.ping(node_info['host'], node_info['port']):
                    try:
                        block_data = self.server.node_client.get_block(
                            node_info['host'], node_info['port'], block_info
                        )
                        if block_data:
                            logger.log("DOWNLOAD", f"Bloque {logical_id} recuperado de réplica: {replica_node}")
                            return block_data
                    except Exception as e:
                        logger.log("DOWNLOAD", f"Error recuperando bloque {logical_id} de réplica {replica_node}: {e}")
        
        logger.log("DOWNLOAD", f"Todos los nodos fallaron para el bloque {logical_id}")
        return None