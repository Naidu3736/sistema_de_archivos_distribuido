# upload_handler.py (VERSIÓN CORREGIDA)
import os
import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class UploadHandler:
    def __init__(self, file_server):
        self.server = file_server

    def process(self, client: socket.socket):
        """Procesa una solicitud de upload del cliente con distribución en nodos"""
        logger.log("UPLOAD", "Iniciando proceso de upload")
        try:
            # Fase 1: Recibir nombre del archivo
            filename = NetworkUtils.receive_filename(client)
            logger.log("UPLOAD", f"Recibido nombre de archivo: {filename}")
            
            # Fase 2: Recibir tamaño del archivo
            file_size = NetworkUtils.receive_file_size(client)
            logger.log("UPLOAD", f"Recibido tamaño de archivo: {file_size}")

            # Fase 3: Verificación preliminar de capacidad
            required_blocks = (file_size + self.server.BLOCK_SIZE - 1) // self.server.BLOCK_SIZE
            logger.log("DEBUG", f"bloques requerido: {required_blocks}")
            
            if not self.server.block_table.has_available_blocks(required_blocks):
                logger.log("UPLOAD", f"Espacio insuficiente en bloque tabla: {filename}")
                NetworkUtils.send_response(client, Response.STORAGE_FULL)
                return None

            # Fase 4: Confirmación para cargar el archivo
            NetworkUtils.send_response(client, Response.SUCCESS)
            
            # Fase 5: Procesamiento en streaming y distribución
            blocks_info = self._process_distributed_upload(client, filename, file_size, required_blocks)
            
            if blocks_info:
                NetworkUtils.send_response(client, Response.UPLOAD_COMPLETE)
                logger.log("UPLOAD", f"Upload distribuido completado - {filename}, Bloques: {len(blocks_info['allocated_blocks'])}")
                return blocks_info
            else:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
                return None
        
        except Exception as e:
            logger.log("UPLOAD", f"Error durante upload distribuido: {str(e)}")
            import traceback
            logger.log("UPLOAD", f"Traceback: {traceback.format_exc()}")
            NetworkUtils.send_response(client, Response.SERVER_ERROR)
            return None

    def _process_distributed_upload(self, client: socket.socket, filename: str, file_size: int, required_blocks: int):
        """Procesa la subida distribuyendo bloques entre nodos con sistema robusto de reservas"""
        logger.log("UPLOAD", f"Procesando upload distribuido: {filename} ({file_size} bytes, {required_blocks} bloques)")
        
        # 1. Reservar bloques lógicos temporalmente
        with self.server.block_table_lock:
            reserved_blocks = self.server.block_table.reserve_blocks(required_blocks)
        
        node_assignments = None
        allocated_blocks = None
        file_id = None
        
        try:
            # 2. Planificar distribución en nodos (sin asignar aún)
            node_assignments = self._plan_node_distribution(required_blocks, file_size)
            logger.log("UPLOAD", f"Planificación completada: {len(node_assignments)} asignaciones")
            
            # 3. Crear entrada en file table (sin bloques asignados aún)
            with self.server.file_table_lock:
                file_id = self.server.file_table.create_file(filename, file_size)
                # No establecemos first_block_id todavía
            
            # 4. Procesar streaming y enviar bloques a nodos con confirmación
            upload_results = self._stream_to_nodes_with_confirmation(
                client, filename, file_size, required_blocks, reserved_blocks, node_assignments
            )
            
            if not upload_results["success"]:
                raise Exception(f"Fallo en upload distribuido: {upload_results['failed_blocks']}")
            
            # 5. Confirmar asignación final de bloques
            with self.server.block_table_lock:
                allocated_blocks = self._confirm_block_allocations(
                    reserved_blocks, node_assignments, upload_results["successful_blocks"]
                )
            
            # 6. Completar file table con primera referencia
            with self.server.file_table_lock:
                if allocated_blocks:
                    self.server.file_table.set_first_block(file_id, allocated_blocks[0])
                    self.server.file_table.update_block_count(file_id, len(allocated_blocks))
            
            return {
                'file_id': file_id,
                'filename': filename,
                'allocated_blocks': allocated_blocks,
                'node_assignments': node_assignments,
                'successful_blocks': len(upload_results["successful_blocks"])
            }
            
        except Exception as e:
            logger.log("UPLOAD", f"Error en upload distribuido: {e}")
            # Limpiar recursos en caso de error
            self._cleanup_failed_upload(filename, reserved_blocks, node_assignments, file_size, file_id)
            raise e

    def _plan_node_distribution(self, num_blocks: int, file_size: int) -> list:
        """Planifica distribución circular estricta: A→B→C→A"""
        node_assignments = []
        
        # Obtener todos los nodos disponibles
        all_nodes = list(self.server.node_manager.nodes.keys())
        if not all_nodes:
            raise Exception("No hay nodos disponibles")
        
        # Ordenar nodos para consistencia
        all_nodes.sort()
        
        if len(all_nodes) < 2:
            raise Exception("Se necesitan al menos 2 nodos para distribución circular")
        
        logger.log("UPLOAD", f"Nodos disponibles para distribución circular: {all_nodes}")
        
        for i in range(num_blocks):
            # Calcular índices para distribución circular
            primary_index = i % len(all_nodes)
            replica_index = (i + 1) % len(all_nodes)
            
            primary_node = all_nodes[primary_index]
            replica_node = all_nodes[replica_index]
            
            # Verificar que el nodo réplica tenga espacio disponible
            replica_info = self.server.node_manager.get_node_info(replica_node)
            if not replica_info or replica_info['available_replica_mb'] <= 0:
                # Si el réplica designado no tiene espacio, buscar alternativo
                alternative_replicas = [
                    node for node in all_nodes 
                    if node != primary_node and 
                    self.server.node_manager.get_node_info(node)['available_replica_mb'] > 0
                ]
                if alternative_replicas:
                    replica_node = alternative_replicas[0]
                    logger.log("UPLOAD", f"Réplica alternativa para bloque {i}: {replica_node}")
                else:
                    replica_node = None
                    logger.log("UPLOAD", f"Advertencia: No hay réplica disponible para bloque {i}")
            
            node_assignments.append((primary_node, [replica_node] if replica_node else []))
        
        # Log de distribución planeada
        distribution_summary = {}
        replica_summary = {}
        
        for primary, replicas in node_assignments:
            if primary not in distribution_summary:
                distribution_summary[primary] = 0
            distribution_summary[primary] += 1
            
            for replica in replicas:
                if replica not in replica_summary:
                    replica_summary[replica] = 0
                replica_summary[replica] += 1
        
        logger.log("UPLOAD", f"Distribución circular - Primarios: {distribution_summary}")
        logger.log("UPLOAD", f"Réplicas: {replica_summary}")
        
        return node_assignments

    def _stream_to_nodes_with_confirmation(self, client: socket.socket, filename: str, file_size: int, 
                                         required_blocks: int, reserved_blocks: list, node_assignments: list):
        """Stream el archivo a nodos con confirmación robusta"""
        bytes_remaining = file_size
        block_index = 0
        successful_blocks = []
        failed_blocks = []
        
        while bytes_remaining > 0 and block_index < required_blocks:
            # Calcular tamaño del bloque actual
            current_block_size = min(self.server.BLOCK_SIZE, bytes_remaining)
            
            # Recibir bloque del cliente
            block_data = NetworkUtils.receive_exact_bytes(client, current_block_size)
            
            # Obtener información de asignación de nodos para este bloque
            logical_id = reserved_blocks[block_index]
            primary_node, replica_nodes = node_assignments[block_index]
            
            # Intentar enviar bloque con manejo de fallos
            block_success = self._send_block_with_fallback(
                primary_node, replica_nodes, block_data, filename, logical_id, block_index
            )
            
            if block_success:
                successful_blocks.append({
                    'logical_id': logical_id,
                    'physical_number': block_index,
                    'primary_node': primary_node,
                    'replica_nodes': block_success['replica_nodes']  # Réplicas que funcionaron
                })
                logger.log("UPLOAD", f"Bloque {block_index} confirmado - Primario: {primary_node}, Réplicas: {len(block_success['replica_nodes'])}")
            else:
                failed_blocks.append(block_index)
                logger.log("UPLOAD", f"Bloque {block_index} falló - No se pudo almacenar")
            
            bytes_remaining -= current_block_size
            block_index += 1
            
            # Mostrar progreso
            progress = (block_index / required_blocks) * 100
            logger.log("UPLOAD", f"Progreso: {progress:.1f}% - Bloque {block_index}/{required_blocks}")
        
        return {
            "success": len(failed_blocks) == 0,
            "successful_blocks": successful_blocks,
            "failed_blocks": failed_blocks
        }

    def _send_block_with_fallback(self, primary_node: str, replica_nodes: list, block_data: bytes, 
                                 filename: str, logical_id: int, block_index: int) -> dict:
        """Envía un bloque con sistema de fallback si algún nodo falla"""
        successful_replicas = []
        
        # 1. Verificar y enviar al nodo primario
        primary_success = self._send_block_to_node_with_allocation(
            primary_node, block_data, filename, logical_id, block_index, is_primary=True
        )
        
        if not primary_success:
            # Intentar con otro nodo como primario
            fallback_primary = self._find_fallback_primary(primary_node, replica_nodes)
            if fallback_primary:
                primary_success = self._send_block_to_node_with_allocation(
                    fallback_primary, block_data, filename, logical_id, block_index, is_primary=True
                )
                if primary_success:
                    primary_node = fallback_primary  # Actualizar nodo primario
                    replica_nodes = [r for r in replica_nodes if r != fallback_primary]  # Remover de réplicas
        
        if not primary_success:
            return None  # No se pudo almacenar el bloque en ningún primario
        
        # 2. Enviar a réplicas con manejo de fallos
        for replica_node in replica_nodes:
            replica_success = self._send_block_to_node_with_allocation(
                replica_node, block_data, filename, logical_id, block_index, is_primary=False
            )
            if replica_success:
                successful_replicas.append(replica_node)
            else:
                logger.log("UPLOAD", f"Réplica falló en nodo {replica_node}, intentando con nodo alternativo")
                
                # Buscar nodo alternativo para réplica
                alternative_node = self._find_alternative_replica_node([primary_node] + successful_replicas)
                if alternative_node:
                    alt_success = self._send_block_to_node_with_allocation(
                        alternative_node, block_data, filename, logical_id, block_index, is_primary=False
                    )
                    if alt_success:
                        successful_replicas.append(alternative_node)
        
        return {
            'primary_node': primary_node,
            'replica_nodes': successful_replicas
        }

    def _send_block_to_node_with_allocation(self, node_id: str, block_data: bytes, filename: str, 
                                          logical_id: int, block_index: int, is_primary: bool = False) -> bool:
        """Envía un bloque a un nodo y asigna recursos si es exitoso"""
        node_info = self.server.node_manager.get_node_info(node_id)
        if not node_info:
            return False
        
        # Verificar que el nodo esté activo
        if not self.server.node_client.ping(node_info['host'], node_info['port']):
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
                node_info['host'], 
                node_info['port'], 
                block_data, 
                block_info
            )
            
            if success:
                # Asignar recursos solo si el envío fue exitoso
                size_mb = len(block_data) / (1024 * 1024)
                if is_primary:
                    allocation_success = self.server.node_manager.allocate_primary(node_id, size_mb)
                else:
                    allocation_success = self.server.node_manager.allocate_replica(node_id, size_mb)
                
                if not allocation_success:
                    logger.log("UPLOAD", f"Error asignando recursos en nodo {node_id}")
                    # Podríamos intentar eliminar el bloque aquí, pero continuamos
                
                node_type = "primario" if is_primary else "réplica"
                logger.log("UPLOAD", f"Bloque {block_index} confirmado en {node_type}: {node_id}")
            
            return success
            
        except Exception as e:
            logger.log("UPLOAD", f"Excepción enviando bloque a {node_id}: {e}")
            return False

    def _find_fallback_primary(self, original_primary: str, replica_nodes: list) -> str:
        """Encuentra un nodo alternativo para primario"""
        # Primero intentar con las réplicas
        for replica_node in replica_nodes:
            node_info = self.server.node_manager.get_node_info(replica_node)
            if node_info and self.server.node_client.ping(node_info['host'], node_info['port']):
                return replica_node
        
        # Buscar cualquier nodo disponible
        candidates = self.server.node_manager.get_primary_candidates()
        for candidate in candidates:
            if candidate != original_primary:
                node_info = self.server.node_manager.get_node_info(candidate)
                if node_info and self.server.node_client.ping(node_info['host'], node_info['port']):
                    return candidate
        
        return None

    def _find_alternative_replica_node(self, exclude_nodes: list) -> str:
        """Encuentra un nodo alternativo para réplica"""
        candidates = self.server.node_manager.get_replica_candidates(exclude_nodes=exclude_nodes)
        for candidate in candidates:
            node_info = self.server.node_manager.get_node_info(candidate)
            if node_info and self.server.node_client.ping(node_info['host'], node_info['port']):
                return candidate
        return None

    def _confirm_block_allocations(self, reserved_blocks: list, original_assignments: list, successful_blocks: list) -> list:
        """Confirma las asignaciones finales de bloques"""
        allocated_blocks = []
        
        for block_info in successful_blocks:
            logical_id = block_info['logical_id']
            physical_number = block_info['physical_number']
            primary_node = block_info['primary_node']
            replica_nodes = block_info['replica_nodes']
            
            # Encontrar el siguiente bloque
            next_block = None
            current_index = reserved_blocks.index(logical_id)
            if current_index < len(reserved_blocks) - 1:
                next_block = reserved_blocks[current_index + 1]
            
            # Confirmar asignación final
            self.server.block_table.confirm_block_allocation(
                logical_id=logical_id,
                primary_node=primary_node,
                replica_nodes=replica_nodes,
                physical_number=physical_number,
                next_block=next_block
            )
            
            allocated_blocks.append(logical_id)
        
        return allocated_blocks

    def _cleanup_failed_upload(self, filename: str, reserved_blocks: list, 
                              node_assignments: list, file_size: int, file_id: int):
        """Limpia recursos en caso de fallo durante el upload"""
        try:
            # Cancelar reservas de bloques
            if reserved_blocks:
                with self.server.block_table_lock:
                    self.server.block_table.cancel_blocks_reservation(reserved_blocks)
            
            # Eliminar entrada de file table
            if file_id is not None:
                with self.server.file_table_lock:
                    self.server.file_table.delete_file(file_id)
                    
            logger.log("UPLOAD", f"Limpieza completada para upload fallido: {filename}")
            
        except Exception as e:
            logger.log("UPLOAD", f"Error durante limpieza de upload fallido: {e}")