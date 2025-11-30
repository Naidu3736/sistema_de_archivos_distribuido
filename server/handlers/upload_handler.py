import os
import socket
from core.protocol import Response
from core.logger import logger
from core.network_utils import NetworkUtils

class UploadHandler:
    def __init__(self, file_server):
        self.server = file_server

    def process(self, client: socket.socket):
        """Procesa upload del cliente"""
        try:
            filename = NetworkUtils.receive_filename(client)
            file_size = NetworkUtils.receive_file_size(client)

            # Verificar si existe
            with self.server.file_table_lock:
                if self.server.file_table.file_exists(filename):
                    NetworkUtils.send_response(client, Response.FILE_ALREADY_EXISTS)
                    return None
            
            # Calcular bloques necesarios
            required_blocks = (file_size + self.server.BLOCK_SIZE - 1) // self.server.BLOCK_SIZE
            if not self.server.block_table.has_available_blocks(required_blocks):
                NetworkUtils.send_response(client, Response.STORAGE_FULL)
                return None

            NetworkUtils.send_response(client, Response.SUCCESS)
            
            # Procesar upload
            result = self._upload_file(client, filename, file_size, required_blocks)
            
            if result:
                NetworkUtils.send_response(client, Response.UPLOAD_COMPLETE)
                logger.log("UPLOAD", f"Upload exitoso: {filename}")
                return result
            else:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
                return None
        
        except Exception as e:
            logger.log("UPLOAD", f"Error: {str(e)}")
            NetworkUtils.send_response(client, Response.SERVER_ERROR)
            return None

    def _upload_file(self, client: socket.socket, filename: str, file_size: int, required_blocks: int):
        """Upload principal simplificado"""
        # Reservar recursos
        with self.server.block_table_lock:
            reserved_blocks = self.server.block_table.reserve_blocks(required_blocks)
        
        with self.server.file_table_lock:
            file_id = self.server.file_table.create_file(filename, file_size)
        
        # Planificar distribución
        node_assignments = self._plan_node_distribution(required_blocks)
        uploaded_blocks = []
        
        try:
            # Distribuir bloques
            for block_index in range(required_blocks):
                block_size = min(self.server.BLOCK_SIZE, file_size - (block_index * self.server.BLOCK_SIZE))
                block_data = NetworkUtils.receive_complete_data(client, block_size)
                
                primary_node, replica_nodes = node_assignments[block_index]
                
                # Enviar bloque con fallback si es necesario
                success = self._send_block_with_fallback(
                    block_data, filename, reserved_blocks[block_index], block_index,
                    primary_node, replica_nodes, uploaded_blocks
                )
                
                if not success:
                    raise Exception(f"Fallo en bloque {block_index}")
            
            # Confirmar todo
            self._confirm_upload(file_id, reserved_blocks, uploaded_blocks)
            
            return {
                'file_id': file_id,
                'filename': filename,
                'allocated_blocks': reserved_blocks
            }
            
        except Exception as e:
            try:
                NetworkUtils.send_response(client, Response.SERVER_ERROR)
            except:
                pass
            self._cleanup_upload(filename, reserved_blocks, file_id, uploaded_blocks)
            raise e

    def _plan_node_distribution(self, num_blocks: int) -> list:
        """Distribución de nodos - versión simplificada"""
        all_nodes = list(self.server.node_manager.nodes.keys())
        if not all_nodes:
            raise Exception("No hay nodos disponibles")
        
        all_nodes.sort()
        node_assignments = []
        
        for i in range(num_blocks):
            primary_node = all_nodes[i % len(all_nodes)]
            replica_node = all_nodes[(i + 1) % len(all_nodes)]
            
            # Verificar espacio para réplica
            if not self.server.node_manager.verify_node_space(replica_node, 1, False):
                replica_node = None
            
            node_assignments.append((primary_node, [replica_node] if replica_node else []))
        
        return node_assignments

    def _send_block_with_fallback(self, block_data: bytes, filename: str, 
                                 logical_id: int, block_index: int,
                                 primary_node: str, replica_nodes: list, 
                                 uploaded_blocks: list) -> bool:
        """Envía bloque con fallback si el primario falla"""
        # Primero intentar con el nodo primario planificado
        if self._send_block(primary_node, block_data, filename, logical_id, block_index, True):
            # Enviar réplicas
            successful_replicas = []
            for replica_node in replica_nodes:
                if self._send_block(replica_node, block_data, filename, logical_id, block_index, False):
                    successful_replicas.append(replica_node)
            
            uploaded_blocks.append({
                'logical_id': logical_id,
                'primary_node': primary_node,
                'replica_nodes': successful_replicas
            })
            return True
        
        # Fallback: buscar nodo primario alternativo
        available_nodes = self._get_available_primary_nodes()
        for alt_node in available_nodes:
            if alt_node != primary_node and self._send_block(alt_node, block_data, filename, logical_id, block_index, True):
                # Enviar réplica para el nodo alternativo
                successful_replicas = []
                replica_candidates = self._get_available_replica_nodes(exclude=[alt_node])
                for replica_node in replica_candidates[:1]:  # Solo 1 réplica
                    if self._send_block(replica_node, block_data, filename, logical_id, block_index, False):
                        successful_replicas.append(replica_node)
                
                uploaded_blocks.append({
                    'logical_id': logical_id,
                    'primary_node': alt_node,
                    'replica_nodes': successful_replicas
                })
                return True
        
        return False

    def _get_available_primary_nodes(self) -> list:
        """Obtiene nodos primarios disponibles"""
        return [node_id for node_id in self.server.node_manager.nodes.keys()
                if self.server.node_manager.verify_node_space(node_id, 1, True)]

    def _get_available_replica_nodes(self, exclude: list = None) -> list:
        """Obtiene nodos réplica disponibles"""
        exclude = exclude or []
        return [node_id for node_id in self.server.node_manager.nodes.keys()
                if node_id not in exclude and 
                self.server.node_manager.verify_node_space(node_id, 1, False)]

    def _send_block(self, node_id: str, block_data: bytes, filename: str, 
                    logical_id: int, block_index: int, is_primary: bool) -> bool:
        """Envía un bloque a un nodo"""
        node_info = self.server.node_manager.get_node_info(node_id)
        if not node_info or not self.server.node_client.ping(node_info['host'], node_info['port']):
            return False
        
        # Asignar espacio
        if is_primary:
            if not self.server.node_manager.allocate_primary(node_id, 1):
                return False
        else:
            if not self.server.node_manager.allocate_replica(node_id, 1):
                return False
        
        # Enviar bloque
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
            
            if not success:
                # Revertir asignación
                if is_primary:
                    self.server.node_manager.free_primary(node_id, 1)
                else:
                    self.server.node_manager.free_replica(node_id, 1)
            
            return success
            
        except Exception:
            # Revertir asignación
            if is_primary:
                self.server.node_manager.free_primary(node_id, 1)
            else:
                self.server.node_manager.free_replica(node_id, 1)
            return False

    def _confirm_upload(self, file_id: int, reserved_blocks: list, uploaded_blocks: list):
        """Confirma la upload exitosa"""
        with self.server.block_table_lock:
            for i, block_info in enumerate(uploaded_blocks):
                next_block = reserved_blocks[i + 1] if i < len(reserved_blocks) - 1 else None
                self.server.block_table.confirm_block_allocation(
                    logical_id=block_info['logical_id'],
                    primary_node=block_info['primary_node'],
                    replica_nodes=block_info['replica_nodes'],
                    physical_number=i,
                    next_block=next_block
                )
        
        with self.server.file_table_lock:
            self.server.file_table.set_first_block(file_id, reserved_blocks[0])
            self.server.file_table.update_block_count(file_id, len(reserved_blocks))

    def _cleanup_upload(self, filename: str, reserved_blocks: list, file_id: int, uploaded_blocks: list):
        """Limpieza simplificada"""
        try:
            # Eliminar bloques físicos
            if uploaded_blocks:
                nodes_with_blocks = set()
                for block in uploaded_blocks:
                    nodes_with_blocks.add(block['primary_node'])
                    nodes_with_blocks.update(block['replica_nodes'])
                
                for node_id in nodes_with_blocks:
                    self._delete_blocks_from_node(node_id, filename)
            
            # Liberar espacio
            for block in uploaded_blocks:
                self.server.node_manager.free_primary(block['primary_node'], 1)
                for replica in block['replica_nodes']:
                    self.server.node_manager.free_replica(replica, 1)
            
            # Limpiar metadatos
            if reserved_blocks:
                with self.server.block_table_lock:
                    self.server.block_table.cancel_blocks_reservation(reserved_blocks)
            
            if file_id is not None:
                with self.server.file_table_lock:
                    self.server.file_table.delete_file(file_id)
                    
        except Exception as e:
            logger.log("CLEANUP", f"Error en limpieza: {e}")

    def _delete_blocks_from_node(self, node_id: str, filename: str):
        """Elimina bloques de un nodo"""
        node_info = self.server.node_manager.get_node_info(node_id)
        if not node_info:
            return
            
        if not self.server.node_client.ping(node_info['host'], node_info['port']):
            return
        
        try:
            self.server.node_client.delete_blocks(node_info['host'], node_info['port'], filename)
        except Exception:
            pass