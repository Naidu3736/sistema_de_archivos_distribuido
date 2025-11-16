import socket
import threading
import time
import json

class Servidor:
    def __init__(self, puerto=8001):
        self.puerto = puerto
        self.conexiones_activas = {}  # {puerto: socket}
        self.conexiones_pendientes = set()  # Puertos a los que estamos intentando conectar
        self.running = True
        
    def iniciar(self):
        print(f"Servidor {self.puerto} iniciando...")
        
        # Cargar metadata de nodos
        metadata = self._cargar_metadata()
        if metadata:
            nodos = [n['id'] for n in metadata['nodos']]
            print(f"Servidores en metadata: {nodos}")
        
        threading.Thread(target=self._escuchar_servidores, daemon=True).start()
        threading.Thread(target=self._escuchar_clientes, daemon=True).start()
        
        time.sleep(2)
        threading.Thread(target=self._conectar_a_otros, daemon=True).start()
        
        print(f"Servidor {self.puerto} LISTO")
        self._mantener_activo()
    
    def _cargar_metadata(self):
        try:
            with open('nodos.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"No se pudo cargar nodos.json: {e}")
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
                
                # Manejar en hilo separado
                threading.Thread(
                    target=self._manejar_conexion_entrante,
                    args=(cliente_sock, addr),
                    daemon=True
                ).start()
                
        except Exception as e:
            print(f"Error en servidor {self.puerto}: {e}")
    
    def _manejar_conexion_entrante(self, sock, addr):
        """Manejar conexiones que otros servidores inician con nosotros"""
        try:
            # Agregar a conexiones activas
            puerto_remoto = addr[1]
            self.conexiones_activas[puerto_remoto] = sock
            
            while self.running:
                data = sock.recv(1024)
                if not data:
                    break
                    
                mensaje = json.loads(data.decode())
                print(f"Servidor {self.puerto}: Mensaje ENTRANTE de {addr}: {mensaje}")
                
                # Si es un HOLA, responder
                if mensaje.get('tipo') == 'HOLA':
                    respuesta = {
                        'tipo': 'HOLA_RESPUESTA',
                        'de': self.puerto,
                        'mensaje': f'Hola servidor {mensaje["de"]}!'
                    }
                    sock.send(json.dumps(respuesta).encode())
                
        except Exception as e:
            print(f"Servidor {self.puerto}: Error con conexión entrante {addr}: {e}")
        finally:
            sock.close()
            if puerto_remoto in self.conexiones_activas:
                del self.conexiones_activas[puerto_remoto]
    
    def _conectar_a_otros(self):
        metadata = self._cargar_metadata()
        if not metadata:
            print(f"Servidor {self.puerto}: No se pudo cargar metadata")
            return
        
        servidores_a_conectar = []
        for nodo in metadata['nodos']:
            if nodo['id'] != self.puerto:  # No conectar consigo mismo
                servidores_a_conectar.append({
                    'host': nodo['host'],
                    'puerto': nodo['puerto']
                })
        
        if not servidores_a_conectar:
            print(f"Servidor {self.puerto}: No hay otros servidores para conectar")
            return
            
        print(f"Servidor {self.puerto}: Conectando a {len(servidores_a_conectar)} servidores...")
        
        for servidor in servidores_a_conectar:
            # Verificar si ya estamos conectados o conectándose
            if servidor['puerto'] not in self.conexiones_activas and servidor['puerto'] not in self.conexiones_pendientes:
                print(f"Intentando conectar a {servidor['host']}:{servidor['puerto']}")
                self._conectar_servidor(servidor)
                time.sleep(1)
            else:
                print(f"Ya conectado o conectándose a {servidor['puerto']}")
    
    def _conectar_servidor(self, servidor):
        """Conectar activamente a otro servidor"""
        self.conexiones_pendientes.add(servidor['puerto'])
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((servidor['host'], servidor['puerto']))
            
            # Agregar a conexiones activas
            self.conexiones_activas[servidor['puerto']] = sock
            self.conexiones_pendientes.remove(servidor['puerto'])
            
            # Enviar mensaje de presentación
            mensaje = {
                'tipo': 'HOLA',
                'de': self.puerto,
                'mensaje': f'Hola desde servidor {self.puerto}'
            }
            sock.send(json.dumps(mensaje).encode())
            
            print(f"Servidor {self.puerto}: Conectado EXITOSAMENTE a {servidor['host']}:{servidor['puerto']}")
            
            # Manejar esta conexión saliente
            threading.Thread(
                target=self._manejar_conexion_saliente,
                args=(sock, (servidor['host'], servidor['puerto'])),
                daemon=True
            ).start()
            
        except socket.timeout:
            print(f"Servidor {self.puerto}: Timeout conectando a {servidor['host']}:{servidor['puerto']}")
            self.conexiones_pendientes.remove(servidor['puerto'])
        except ConnectionRefusedError:
            print(f"Servidor {self.puerto}: Conexión rechazada por {servidor['host']}:{servidor['puerto']}")
            self.conexiones_pendientes.remove(servidor['puerto'])
        except Exception as e:
            print(f"Servidor {self.puerto}: Error conectando a {servidor['host']}:{servidor['puerto']}: {e}")
            self.conexiones_pendientes.remove(servidor['puerto'])
    
    def _manejar_conexion_saliente(self, sock, addr):
        """Manejar conexiones que nosotros iniciamos"""
        try:
            while self.running:
                data = sock.recv(1024)
                if not data:
                    break
                    
                mensaje = json.loads(data.decode())
                print(f"Servidor {self.puerto}: Mensaje SALIENTE de {addr}: {mensaje}")
                
        except Exception as e:
            print(f"Servidor {self.puerto}: Error con conexión saliente {addr}: {e}")
        finally:
            sock.close()
            if addr[1] in self.conexiones_activas:
                del self.conexiones_activas[addr[1]]
    
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