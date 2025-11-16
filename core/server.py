import socket
import threading
import time
import json
import os
from split_union import split, union, clean_blocks, BLOCK_SIZE

class Servidor:
    def __init__(self, host='localhost', puerto=8001, otros_servidores=None, capacidad_mb=100):
        self.host = host
        self.puerto = puerto
        self.otros_servidores = otros_servidores or []
        self.capacidad_mb = capacidad_mb
        self.conexiones_activas = {}
        self.running = True
        self.tabla_bloques_global = None
        self.blocks_dir = f"blocks_{puerto}"
        self.archivos_metadata = {}
        os.makedirs(self.blocks_dir, exist_ok=True)
        
    def iniciar(self):
        print(f"Iniciando servidor en puerto {self.puerto}")
        
        threading.Thread(target=self._escuchar_servidores, daemon=True).start()
        threading.Thread(target=self._escuchar_clientes, daemon=True).start()
        
        time.sleep(2)
        
        threading.Thread(target=self._conectar_a_otros_servidores, daemon=True).start()
        threading.Thread(target=self._enviar_heartbeats, daemon=True).start()
        
        self._mantener_servidor_activo()
    
    def _escuchar_servidores(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.puerto))
            sock.listen(5)
            
            print(f"Servidor escuchando en {self.host}:{self.puerto}")
            
            while self.running:
                try:
                    cliente_sock, addr = sock.accept()
                    print(f"Servidor conectado desde {addr}")
                    
                    threading.Thread(
                        target=self._manejar_servidor_conectado,
                        args=(cliente_sock, addr),
                        daemon=True
                    ).start()
                    
                except Exception as e:
                    if self.running:
                        print(f"Error aceptando conexion: {e}")
        except Exception as e:
            print(f"Error en escucha de servidores: {e}")
    
    def _escuchar_clientes(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            puerto_clientes = self.puerto + 1000
            sock.bind((self.host, puerto_clientes))
            sock.listen(5)
            
            print(f"Escuchando clientes en puerto {puerto_clientes}")
            
            while self.running:
                try:
                    cliente_sock, addr = sock.accept()
                    print(f"Cliente conectado desde {addr}")
                    
                    threading.Thread(
                        target=self._manejar_cliente,
                        args=(cliente_sock, addr),
                        daemon=True
                    ).start()
                    
                except Exception as e:
                    if self.running:
                        print(f"Error con cliente: {e}")
        except Exception as e:
            print(f"Error en escucha de clientes: {e}")
    
    def _manejar_cliente(self, sock, addr):
        try:
            while self.running:
                data = sock.recv(1024)
                if not data:
                    break
                
                try:
                    mensaje = json.loads(data.decode())
                    self._procesar_comando_cliente(mensaje, sock, addr)
                except json.JSONDecodeError:
                    print(f"Mensaje no JSON de {addr}: {data.decode()}")
                    
        except Exception as e:
            print(f"Error manejando cliente {addr}: {e}")
        finally:
            sock.close()
    
    def _procesar_comando_cliente(self, mensaje, sock, addr):
        comando = mensaje.get('comando')
        
        if comando == 'SUBIR_ARCHIVO':
            self._manejar_subida_archivo(mensaje, sock, addr)
        elif comando == 'DESCARGAR_ARCHIVO':
            self._manejar_descarga_archivo(mensaje, sock, addr)
        elif comando == 'LISTAR_ARCHIVOS':
            self._manejar_listar_archivos(mensaje, sock, addr)
        else:
            respuesta = {'estado': 'error', 'mensaje': 'Comando desconocido'}
            sock.send(json.dumps(respuesta).encode())
    
    def _manejar_subida_archivo(self, mensaje, sock, addr):
        if not self.tabla_bloques_global:
            respuesta = {'estado': 'error', 'mensaje': 'Sistema no inicializado'}
            sock.send(json.dumps(respuesta).encode())
            return
        
        nombre_archivo = mensaje.get('nombre_archivo')
        datos_archivo = mensaje.get('datos')
        
        if not datos_archivo:
            respuesta = {'estado': 'error', 'mensaje': 'No se recibieron datos'}
            sock.send(json.dumps(respuesta).encode())
            return
        
        # Convertir datos de base64 a bytes
        import base64
        try:
            datos_bytes = base64.b64decode(datos_archivo)
        except:
            respuesta = {'estado': 'error', 'mensaje': 'Error decodificando datos'}
            sock.send(json.dumps(respuesta).encode())
            return
        
        tamano_archivo = len(datos_bytes)
        bloques_necesarios = (tamano_archivo + BLOCK_SIZE - 1) // BLOCK_SIZE
        archivo_id = f"{nombre_archivo}_{int(time.time())}"
        
        bloques_asignados = self.tabla_bloques_global.asignar_bloques(bloques_necesarios, archivo_id)
        
        if not bloques_asignados:
            respuesta = {'estado': 'error', 'mensaje': 'No hay espacio suficiente'}
            sock.send(json.dumps(respuesta).encode())
            return
        
        # Distribuir físicamente los bloques entre nodos
        self._distribuir_bloques_entre_nodos(archivo_id, bloques_asignados, datos_bytes)
        
        respuesta = {
            'estado': 'ok',
            'archivo_id': archivo_id,
            'bloques_asignados': bloques_asignados,
            'bloques_necesarios': bloques_necesarios
        }
        sock.send(json.dumps(respuesta).encode())
        
        self._notificar_archivo_subido(archivo_id, bloques_asignados)
    
    def _distribuir_bloques_entre_nodos(self, archivo_id, bloques_asignados, datos_archivo):
        bloques_datos = self._dividir_en_bloques(datos_archivo)
        
        for i, bloque_id in enumerate(bloques_asignados):
            if i < len(bloques_datos):
                nodo_destino = self.tabla_bloques_global._encontrar_nodo(bloque_id)
                bloque_data = bloques_datos[i]
                
                if nodo_destino == self.puerto:
                    self._guardar_bloque_local(archivo_id, bloque_id, bloque_data)
                    print(f"Bloque {bloque_id} guardado localmente")
                else:
                    self._enviar_bloque_a_nodo(nodo_destino, archivo_id, bloque_id, bloque_data)
    
    def _dividir_en_bloques(self, datos):
        return [datos[i:i+BLOCK_SIZE] for i in range(0, len(datos), BLOCK_SIZE)]
    
    def _guardar_bloque_local(self, archivo_id, bloque_id, datos):
        bloque_filename = f"{archivo_id}_bloque_{bloque_id}.bin"
        bloque_path = os.path.join(self.blocks_dir, bloque_filename)
        
        with open(bloque_path, 'wb') as f:
            f.write(datos)
    
    def _enviar_bloque_a_nodo(self, nodo_destino, archivo_id, bloque_id, datos):
        if nodo_destino in self.conexiones_activas:
            import base64
            mensaje = {
                'tipo': 'GUARDAR_BLOQUE',
                'archivo_id': archivo_id,
                'bloque_id': bloque_id,
                'datos': base64.b64encode(datos).decode('utf-8')
            }
            sock = self.conexiones_activas[nodo_destino]
            sock.send(json.dumps(mensaje).encode())
            print(f"Bloque {bloque_id} enviado al nodo {nodo_destino}")
    
    def _manejar_descarga_archivo(self, mensaje, sock, addr):
        archivo_id = mensaje.get('archivo_id')
        
        if archivo_id not in self.archivos_metadata:
            respuesta = {'estado': 'error', 'mensaje': 'Archivo no encontrado'}
            sock.send(json.dumps(respuesta).encode())
            return
        
        # Reconstruir archivo desde bloques distribuidos
        archivo_reconstruido = self._reconstruir_archivo(archivo_id)
        
        if archivo_reconstruido:
            import base64
            respuesta = {
                'estado': 'ok',
                'archivo_id': archivo_id,
                'datos': base64.b64encode(archivo_reconstruido).decode('utf-8')
            }
        else:
            respuesta = {'estado': 'error', 'mensaje': 'Error reconstruyendo archivo'}
        
        sock.send(json.dumps(respuesta).encode())
    
    def _reconstruir_archivo(self, archivo_id):
        try:
            bloques_archivo = self.archivos_metadata.get(archivo_id, [])
            datos_completos = b''
            
            for bloque_id in bloques_archivo:
                bloque_data = self._obtener_bloque(archivo_id, bloque_id)
                if bloque_data:
                    datos_completos += bloque_data
                else:
                    print(f"Error: No se pudo obtener bloque {bloque_id}")
                    return None
            
            return datos_completos
        except Exception as e:
            print(f"Error reconstruyendo archivo {archivo_id}: {e}")
            return None
    
    def _obtener_bloque(self, archivo_id, bloque_id):
        # Primero intentar obtener localmente
        bloque_filename = f"{archivo_id}_bloque_{bloque_id}.bin"
        bloque_path = os.path.join(self.blocks_dir, bloque_filename)
        
        if os.path.exists(bloque_path):
            with open(bloque_path, 'rb') as f:
                return f.read()
        
        # Si no está localmente, pedir al nodo correspondiente
        nodo_destino = self.tabla_bloques_global._encontrar_nodo(bloque_id)
        if nodo_destino and nodo_destino in self.conexiones_activas:
            return self._solicitar_bloque_a_nodo(nodo_destino, archivo_id, bloque_id)
        
        return None
    
    def _solicitar_bloque_a_nodo(self, nodo_destino, archivo_id, bloque_id):
        try:
            mensaje = {
                'tipo': 'SOLICITAR_BLOQUE',
                'archivo_id': archivo_id,
                'bloque_id': bloque_id
            }
            sock = self.conexiones_activas[nodo_destino]
            sock.send(json.dumps(mensaje).encode())
            
            # Esperar respuesta (en una implementación real necesitarías un sistema de espera)
            return b''  # Placeholder
        except Exception as e:
            print(f"Error solicitando bloque {bloque_id} al nodo {nodo_destino}: {e}")
            return None
    
    def _manejar_listar_archivos(self, mensaje, sock, addr):
        archivos = list(self.archivos_metadata.keys())
        respuesta = {
            'estado': 'ok',
            'archivos': archivos
        }
        sock.send(json.dumps(respuesta).encode())
    
    def _notificar_archivo_subido(self, archivo_id, bloques_asignados):
        mensaje = {
            'tipo': 'ARCHIVO_SUBIDO',
            'archivo_id': archivo_id,
            'bloques_asignados': bloques_asignados,
            'timestamp': time.time()
        }
        self.enviar_mensaje_a_todos(mensaje)
    
    def _conectar_a_otros_servidores(self):
        print(f"Conectando a {len(self.otros_servidores)} servidores...")
        
        for servidor in self.otros_servidores:
            threading.Thread(
                target=self._intentar_conexion_servidor,
                args=(servidor,),
                daemon=True
            ).start()
            time.sleep(1)
    
    def _intentar_conexion_servidor(self, servidor):
        max_intentos = 3
        intento = 0
        
        while intento < max_intentos and self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((servidor['host'], servidor['puerto']))
                
                self.conexiones_activas[servidor['puerto']] = sock
                
                mensaje_presentacion = {
                    'tipo': 'HOLA',
                    'desde_puerto': self.puerto,
                    'capacidad_mb': self.capacidad_mb,
                    'timestamp': time.time()
                }
                sock.send(json.dumps(mensaje_presentacion).encode())
                
                print(f"Conectado a servidor {servidor['host']}:{servidor['puerto']}")
                
                threading.Thread(
                    target=self._manejar_servidor_conectado,
                    args=(sock, (servidor['host'], servidor['puerto'])),
                    daemon=True
                ).start()
                
                return
                
            except Exception as e:
                intento += 1
                print(f"Intento {intento} fallido para {servidor['puerto']}: {e}")
                if intento < max_intentos:
                    time.sleep(2)
    
    def _manejar_servidor_conectado(self, sock, addr):
        try:
            while self.running:
                data = sock.recv(1024)
                if not data:
                    break
                
                try:
                    mensaje = json.loads(data.decode())
                    self._procesar_mensaje_servidor(mensaje, sock, addr)
                except json.JSONDecodeError:
                    mensaje_str = data.decode().strip()
                    self._procesar_mensaje_simple(mensaje_str, addr)
                    
        except Exception as e:
            print(f"Error manejando servidor {addr}: {e}")
        finally:
            self._eliminar_conexion(sock, addr)
    
    def _procesar_mensaje_servidor(self, mensaje, sock, addr):
        tipo = mensaje.get('tipo')
        
        if tipo == 'HOLA':
            puerto_remoto = mensaje.get('desde_puerto')
            capacidad_remota = mensaje.get('capacidad_mb')
            print(f"Servidor {puerto_remoto} dijo hola desde {addr}, capacidad: {capacidad_remota}MB")
            
            respuesta = {
                'tipo': 'HOLA_RESPUESTA',
                'desde_puerto': self.puerto,
                'mensaje': f'Hola servidor {puerto_remoto}!',
                'capacidad_mb': self.capacidad_mb
            }
            sock.send(json.dumps(respuesta).encode())
            
            self._inicializar_tabla_si_listo()
            
        elif tipo == 'HOLA_RESPUESTA':
            print(f"{mensaje.get('mensaje')}")
            
        elif tipo == 'HEARTBEAT':
            respuesta = {
                'tipo': 'HEARTBEAT_RESPUESTA',
                'desde_puerto': self.puerto,
                'timestamp': time.time()
            }
            sock.send(json.dumps(respuesta).encode())
            
        elif tipo == 'HEARTBEAT_RESPUESTA':
            pass
            
        elif tipo == 'ARCHIVO_SUBIDO':
            archivo_id = mensaje.get('archivo_id')
            bloques_asignados = mensaje.get('bloques_asignados')
            self.archivos_metadata[archivo_id] = bloques_asignados
            print(f"Servidor {addr} notifico nuevo archivo: {archivo_id}")
            
        elif tipo == 'GUARDAR_BLOQUE':
            archivo_id = mensaje.get('archivo_id')
            bloque_id = mensaje.get('bloque_id')
            datos_b64 = mensaje.get('datos')
            
            import base64
            datos = base64.b64decode(datos_b64)
            self._guardar_bloque_local(archivo_id, bloque_id, datos)
            print(f"Bloque {bloque_id} del archivo {archivo_id} guardado localmente por solicitud de {addr}")
            
        elif tipo == 'SOLICITAR_BLOQUE':
            archivo_id = mensaje.get('archivo_id')
            bloque_id = mensaje.get('bloque_id')
            
            bloque_data = self._obtener_bloque(archivo_id, bloque_id)
            if bloque_data:
                import base64
                respuesta = {
                    'tipo': 'BLOQUE_ENVIADO',
                    'archivo_id': archivo_id,
                    'bloque_id': bloque_id,
                    'datos': base64.b64encode(bloque_data).decode('utf-8')
                }
                sock.send(json.dumps(respuesta).encode())
            
        elif tipo == 'BLOQUE_ENVIADO':
            # Manejar bloque recibido (para implementación completa)
            pass
            
        else:
            print(f"Mensaje de {addr}: {mensaje}")
    
    def _inicializar_tabla_si_listo(self):
        if len(self.conexiones_activas) + 1 == len(self.otros_servidores) + 1:
            self._inicializar_tabla_global()
    
    def _inicializar_tabla_global(self):
        nodos_info = []
        
        for nodo_puerto, sock in self.conexiones_activas.items():
            nodos_info.append({
                'id': nodo_puerto,
                'capacidad_mb': 100,  # Asumimos misma capacidad para simplificar
                'ip': 'localhost',
                'puerto': nodo_puerto
            })
        
        nodos_info.append({
            'id': self.puerto,
            'capacidad_mb': self.capacidad_mb,
            'ip': self.host,
            'puerto': self.puerto
        })
        
        from tabla_bloques import TablaBloques
        self.tabla_bloques_global = TablaBloques(nodos_info)
        print(f"Tabla de bloques inicializada: {self.tabla_bloques_global.capacidad_total} MB totales")
    
    def _procesar_mensaje_simple(self, mensaje, addr):
        if mensaje.startswith("HOLA"):
            print(f"Mensaje simple de {addr}: {mensaje}")
    
    def _enviar_heartbeats(self):
        while self.running:
            time.sleep(10)
            
            for puerto, sock in list(self.conexiones_activas.items()):
                try:
                    heartbeat = {
                        'tipo': 'HEARTBEAT',
                        'desde_puerto': self.puerto,
                        'timestamp': time.time()
                    }
                    sock.send(json.dumps(heartbeat).encode())
                except Exception as e:
                    print(f"Error enviando heartbeat a {puerto}: {e}")
                    self._eliminar_conexion(sock, ('unknown', puerto))
    
    def _eliminar_conexion(self, sock, addr):
        try:
            sock.close()
        except:
            pass
            
        for puerto, socket_obj in list(self.conexiones_activas.items()):
            if socket_obj == sock:
                del self.conexiones_activas[puerto]
                print(f"Conexion con servidor {puerto} cerrada")
                break
    
    def _mantener_servidor_activo(self):
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Cerrando servidor...")
            self.running = False
    
    def enviar_mensaje_a_todos(self, mensaje):
        for puerto, sock in list(self.conexiones_activas.items()):
            try:
                sock.send(json.dumps(mensaje).encode())
            except Exception as e:
                print(f"Error enviando mensaje a {puerto}: {e}")