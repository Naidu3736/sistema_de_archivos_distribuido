# upload_handler.py (VERSIÓN REDUCIDA)
import os
import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class UploadHandler:
    def __init__(self, file_server):
        self.server = file_server

    def process(self, client: socket.socket):
        """Procesa upload con distribución en nodos - versión reducida"""
        try:
            # Fase 1: Recibir metadata
            filename = NetworkUtils.receive_filename(client)
            file_size = NetworkUtils.receive_file_size(client)

            with self.server.file_table_lock:
                if self.server.file_table.file_exists(filename):
                    logger.log("UPLOAD", f"Archivo ya existe: {filename}")
                    NetworkUtils.send_response(client, Response.FILE_ALREADY_EXISTS)
                    return None
            
            # Verificar capacidad
            required_blocks = (file_size + self.server.BLOCK_SIZE - 1) // self.server.BLOCK_SIZE
            if not self.server.block_table.has_available_blocks(required_blocks):
                NetworkUtils.send_response(client, Response.STORAGE_FULL)
                return None

            NetworkUtils.send_response(client, Response.SUCCESS)
            
            # Fase 2: Procesamiento distribuido
            blocks_info = self._process_distributed_upload(client, filename, file_size, required_blocks)
            
            if blocks_info:
                NetworkUtils.send_response(client, Response.UPLOAD_COMPLETE)
                logger.log("UPLOAD", f"Upload completado: {filename}, Bloques: {len(blocks_info['allocated_blocks'])}")
                return blocks_info
            else:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
                return None
        
        except Exception as e:
            logger.log("UPLOAD", f"Error: {str(e)}")
            NetworkUtils.send_response(client, Response.SERVER_ERROR)
            return None

    def _process_distributed_upload(self, client: socket.socket, filename: str, file_size: int, required_blocks: int):
        """Procesa subida distribuyendo bloques - versión reducida"""
        logger.log("UPLOAD", f"Iniciando upload: {filename} ({file_size} bytes, {required_blocks} bloques)")
        
        # 1. Reservar bloques
        with self.server.block_table_lock:
            reserved_blocks = self.server.block_table.reserve_blocks(required_blocks)
        
        # 2. Planificar distribución
        node_assignments = self._plan_node_distribution(required_blocks)
        
        # 3. Crear entrada de archivo
        with self.server.file_table_lock:
            file_id = self.server.file_table.create_file(filename, file_size)
        
        try:
            # 4. Stream y distribución
            upload_results = self._stream_and_distribute(
                client, file_size, required_blocks, reserved_blocks, node_assignments, filename
            )
            
            if not upload_results["success"]:
                raise Exception(f"Bloques fallidos: {upload_results['failed_blocks']}")
            
            # 5. Confirmar asignaciones
            with self.server.block_table_lock:
                allocated_blocks = self._confirm_allocations(reserved_blocks, upload_results["successful_blocks"])
            
            # 6. Completar file table
            with self.server.file_table_lock:
                if allocated_blocks:
                    self.server.file_table.set_first_block(file_id, allocated_blocks[0])
                    self.server.file_table.update_block_count(file_id, len(allocated_blocks))
            
            return {
                'file_id': file_id,
                'filename': filename,
                'allocated_blocks': allocated_blocks,
                'node_assignments': node_assignments
            }
            
        except Exception as e:
            self._cleanup_failed_upload(filename, reserved_blocks, file_id)
            raise e

    def _plan_node_distribution(self, num_blocks: int) -> list:
        """Distribución circular simple: A→B→C→A"""
        all_nodes = list(self.server.node_manager.nodes.keys())
        if not all_nodes:
            raise Exception("No hay nodos disponibles")
        
        all_nodes.sort()
        node_assignments = []
        
        for i in range(num_blocks):
            primary_index = i % len(all_nodes)
            replica_index = (i + 1) % len(all_nodes)
            
            primary_node = all_nodes[primary_index]
            replica_node = all_nodes[replica_index]
            
            # Verificar réplica tiene espacio
            replica_info = self.server.node_manager.get_node_info(replica_node)
            if not replica_info or replica_info['available_replica_mb'] <= 0:
                replica_node = None
            
            node_assignments.append((primary_node, [replica_node] if replica_node else []))
        
        logger.log("UPLOAD", f"Distribución planificada: {len(node_assignments)} bloques")
        return node_assignments

    def _stream_and_distribute(self, client: socket.socket, file_size: int, required_blocks: int,
                             reserved_blocks: list, node_assignments: list, filename: str):
        """Stream con distribución a nodos"""
        bytes_remaining = file_size
        successful_blocks = []
        failed_blocks = []
        
        for block_index in range(required_blocks):
            # Recibir bloque
            current_block_size = min(self.server.BLOCK_SIZE, bytes_remaining)
            block_data = NetworkUtils.receive_complete_data(client, current_block_size)
            
            # Distribuir a nodos
            logical_id = reserved_blocks[block_index]
            primary_node, replica_nodes = node_assignments[block_index]
            
            success = self._distribute_block(primary_node, replica_nodes, block_data, filename, logical_id, block_index)
            
            if success:
                successful_blocks.append({
                    'logical_id': logical_id,
                    'physical_number': block_index,
                    'primary_node': primary_node,
                    'replica_nodes': success['replica_nodes']
                })
            else:
                failed_blocks.append(block_index)
            
            bytes_remaining -= current_block_size
            
            # Log de progreso cada 10 bloques
            if block_index % 10 == 0:
                logger.log("UPLOAD", f"Progreso: {block_index}/{required_blocks} bloques")
        
        return {
            "success": len(failed_blocks) == 0,
            "successful_blocks": successful_blocks,
            "failed_blocks": failed_blocks
        }

    def _distribute_block(self, primary_node: str, replica_nodes: list, block_data: bytes,
                         filename: str, logical_id: int, block_index: int) -> dict:
        """Distribuye bloque a primario y réplicas"""
        # Enviar a primario
        primary_success = self._send_to_node(primary_node, block_data, filename, logical_id, block_index, True)
        if not primary_success:
            return None
        
        # Enviar a réplicas
        successful_replicas = []
        for replica_node in replica_nodes:
            if self._send_to_node(replica_node, block_data, filename, logical_id, block_index, False):
                successful_replicas.append(replica_node)
        
        return {
            'primary_node': primary_node,
            'replica_nodes': successful_replicas
        }

    def _send_to_node(self, node_id: str, block_data: bytes, filename: str,
                     logical_id: int, block_index: int, is_primary: bool) -> bool:
        """Envía bloque a un nodo específico"""
        node_info = self.server.node_manager.get_node_info(node_id)
        if not node_info or not self.server.node_client.ping(node_info['host'], node_info['port']):
            return False
        
        block_info = {
            'block_id': logical_id,
            'filename': filename,
            'physical_number': block_index,
            'size': len(block_data),
            'is_replica': not is_primary
        }
        
        try:
            success = self.server.node_client.send_block(
                node_info['host'], node_info['port'], block_data, block_info
            )
            
            if success:
                # Asignar recursos
                size_mb = len(block_data) / (1024 * 1024)
                if is_primary:
                    self.server.node_manager.allocate_primary(node_id, size_mb)
                else:
                    self.server.node_manager.allocate_replica(node_id, size_mb)
            
            return success
            
        except Exception:
            return False

    def _confirm_allocations(self, reserved_blocks: list, successful_blocks: list) -> list:
        """Confirma asignaciones finales"""
        allocated_blocks = []
        
        for block_info in successful_blocks:
            logical_id = block_info['logical_id']
            
            # Configurar siguiente bloque
            current_index = reserved_blocks.index(logical_id)
            next_block = reserved_blocks[current_index + 1] if current_index < len(reserved_blocks) - 1 else None
            
            self.server.block_table.confirm_block_allocation(
                logical_id=logical_id,
                primary_node=block_info['primary_node'],
                replica_nodes=block_info['replica_nodes'],
                physical_number=block_info['physical_number'],
                next_block=next_block
            )
            
            allocated_blocks.append(logical_id)
        
        return allocated_blocks

    def _cleanup_failed_upload(self, filename: str, reserved_blocks: list, file_id: int):
        """Limpieza simplificada en caso de fallo"""
        try:
            if reserved_blocks:
                with self.server.block_table_lock:
                    self.server.block_table.cancel_blocks_reservation(reserved_blocks)
            
            if file_id is not None:
                with self.server.file_table_lock:
                    self.server.file_table.delete_file(file_id)
                    
            logger.log("UPLOAD", f"Limpieza completada para: {filename}")
            
        except Exception as e:
            logger.log("UPLOAD", f"Error en limpieza: {e}")