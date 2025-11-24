import socket
import json
import os
from typing import List, Dict, Tuple
from core.protocol import Command, Response
from core.logger import logger
from nodes import node_manager

class Peer2Peer:
    def __init__(self, host: str = '0.0.0.0', port: int = 8002, buffer_size: int = 4096):
        self.host = host
        self.port = port
        self.BUFFER_SIZE = buffer_size

        self.active_connections: Dict[int, Tuple[socket.socket, bool]] = {}
        logger.log("P2P", f"Nodo P2P configurado - Escuchando en {host}:{port}")

    def connect(self) -> bool:
        """Conectar con todos los nodos del sistema"""
        if node_manager.get_node_count() <= 1:
            logger.log("P2P", "Solo hay un nodo en el sistema")
            return False
        
        connections = 0
        current_node_id = node_manager.get_id_of_node(self.host, self.port)
        
        for node_id in node_manager.get_all_ids():
            if node_id == current_node_id:
                continue  # Saltarse a sí mismo

            if self._connect_single_node(node_id):   
                connections += 1
        
        return len(self.active_connections) > 0
    
    def _connect_single_node(self, node_id: int) -> bool:
        """Conectar con un solo nodo"""
        if node_id in self.active_connections:
            return True
        
        address = node_manager.get_node_address(node_id)
        if not address:
            return False
            
        host, port = address
        try:
            socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket.connect((host, port))
            self.active_connections[node_id] = (socket, True)
            logger.log("P2P", f"Conectado a {host}:{port}")
            return True
        except Exception as e:
            logger.log("P2P", f"Error conectando a {host}:{port}: {e}")
            return False

    def disconnect(self):
        """Desconectar de todos los nodos"""
        for node_id in list(self.active_connections.keys()):
            self._disconnect_single_node(node_id)
            
        logger.log("P2P", "Desconectado de todos lo nodos")

    def remove_connection(self, node_id: int):
        """Reomover completamente una conexión"""
        self._disconnect_single_node(node_id)

    def _disconnect_single_node(self, node_id: int):
        """Desconectar con un solo nodo"""
        if node_id not in self.active_connections:
            return
        
        socket, _ = self.active_connections[node_id]
        if socket:
            try:
                socket.send(Command.DISCONNECT.to_bytes())
            except:
                pass
        del self.active_connections[node_id]

    def ensure_connection(self, node_id: int) -> bool:
        """Asegurar que hay conexión con un nodo especifico"""
        if node_id in self.active_connections:
            socket, connected = self.active_connections[node_id]

            if connected:
                try:
                    socket.send(Command.HEARTBEAT.to_bytes())
                    return True
                
                except:
                    self.remove_conection(node_id)

        return self._connect_single_node(node_id)
    
    def _reconnect_node(self, node_id: int) -> bool:
        """Reconectar con un nodo"""
        if node_id in self.active_connections:
            return self._connect_single_node(node_id)
        
        old_socket, _ = self.active_connections[node_id]
        if old_socket:
            try:
                old_socket.close()
            except:
                pass
        
        address = node_manager.get_node_address(node_id)
        if not address:
            logger.log("P2P", f"No se encontró la dirección para el nodo {node_id}")
            return False
        
        host, port = address
        try:
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_socket.connect((host, port))

            self.active_connections[node_id] = (new_socket, True)
            logger.log("P2P", f"Reconectado a {host}:{port}")
            return True
        
        except Exception as e:
            logger.log("P2P", f"Fallo reconexión a {host}:{port}: {e}")
            self.active_connections[node_id] = (None, False)
            return False

