import socket
import threading
import time
import json

class Servidor:
    def __init__(self, puerto=8001, otros_servidores=None):
        self.puerto = puerto
        self.otros_servidores = otros_servidores or []
        self.conexiones_activas = {}
        self.running = True
        
    def iniciar(self):
        print(f"Servidor {self.puerto} iniciando...")
        
        # Cargar metadata de nodos
        metadata = self._cargar_metadata()
        if metadata:
            print(f"Servidores en metadata: {[n['id'] for n in metadata['nodos']]}")
        
        threading.Thread(target=self._escuchar_servidores, daemon=True).start()
        threading.Thread(target=self._escuchar_clientes, daemon=True).start()
        
        time.sleep(1)
        threading.Thread(target=self._conectar_a_otros, daemon=True).start()
        
        print(f"Servidor {self.puerto} LISTO")
        self._mantener_activo()
    
    def _cargar_metadata(self):
        """Cargar metadata desde archivo JSON"""
        try:
            with open('metadata_nodos.json', 'r') as f:
                return json.load(f)
        except:
            print("No se pudo cargar metadata_nodos.json")
            return None
    
    def _escuchar_servidores(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', self.puerto))
            sock.listen(5)
            
            print(f"Servidor {self.puerto} escuchando en puerto {self.puerto}")
            
            while self.running:
                cliente_sock, addr = sock.accept()
                print(f"Servidor {self.puerto}: Conexión entrante de {addr}")
                
                threading.Thread(
                    target=self._manejar_conexion,
                    args=(cliente_sock, addr),
                    daemon=True
                ).start()
                
        except Exception as e:
            print(f"Error en servidor {self.puerto}: {e}")
    
    def _escuchar_clientes(self):
        try:
            puerto_clientes = self.puerto + 1000
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', puerto_clientes))
            sock.listen(5)
            
            print(f"Servidor {self.puerto} escuchando clientes en puerto {puerto_clientes}")
            
            while self.running:
                cliente_sock, addr = sock.accept()
                print(f"Servidor {self.puerto}: Cliente conectado desde {addr}")
                
                threading.Thread(
                    target=self._manejar_cliente,
                    args=(cliente_sock, addr),
                    daemon=True
                ).start()
                
        except Exception as e:
            print(f"Error escuchando clientes en {self.puerto}: {e}")
    
    def _conectar_a_otros(self):
        # Usar metadata o la lista configurada
        metadata = self._cargar_metadata()
        servidores_a_conectar = []
        
        if metadata:
            for nodo in metadata['nodos']:
                if nodo['id'] != self.puerto:  # No conectar consigo mismo
                    servidores_a_conectar.append({
                        'host': nodo['host'],
                        'puerto': nodo['puerto']
                    })
        else:
            servidores_a_conectar = self.otros_servidores
        
        if not servidores_a_conectar:
            print(f"Servidor {self.puerto}: No hay otros servidores para conectar")
            return
            
        print(f"Servidor {self.puerto}: Conectando a {len(servidores_a_conectar)} servidores...")
        
        for servidor in servidores_a_conectar:
            threading.Thread(
                target=self._conectar_servidor,
                args=(servidor,),
                daemon=True
            ).start()
            time.sleep(0.5)
    
    def _conectar_servidor(self, servidor):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((servidor['host'], servidor['puerto']))
            
            self.conexiones_activas[servidor['puerto']] = sock
            
            mensaje = {
                'tipo': 'HOLA',
                'de': self.puerto,
                'mensaje': f'Hola desde servidor {self.puerto}'
            }
            sock.send(json.dumps(mensaje).encode())
            
            print(f"Servidor {self.puerto}: Conectado a {servidor['host']}:{servidor['puerto']}")
            
            threading.Thread(
                target=self._manejar_conexion,
                args=(sock, (servidor['host'], servidor['puerto'])),
                daemon=True
            ).start()
            
        except Exception as e:
            print(f"Servidor {self.puerto}: Error conectando a {servidor['host']}:{servidor['puerto']}: {e}")
    
    def _manejar_conexion(self, sock, addr):
        try:
            while self.running:
                data = sock.recv(1024)
                if not data:
                    break
                    
                mensaje = json.loads(data.decode())
                print(f"Servidor {self.puerto}: Mensaje de {addr}: {mensaje}")
                
        except Exception as e:
            print(f"Servidor {self.puerto}: Error con {addr}: {e}")
        finally:
            sock.close()
    
    def _manejar_cliente(self, sock, addr):
        try:
            data = sock.recv(1024)
            if data:
                mensaje = data.decode()
                print(f"Servidor {self.puerto}: Cliente {addr} dice: {mensaje}")
                
                respuesta = f"Servidor {self.puerto} recibio: {mensaje}"
                sock.send(respuesta.encode())
                
        except Exception as e:
            print(f"Servidor {self.puerto}: Error con cliente {addr}: {e}")
        finally:
            sock.close()
    
    def _mantener_activo(self):
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"Servidor {self.puerto} cerrando...")
            self.running = False