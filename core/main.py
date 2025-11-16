import socket
import json
import time
import base64
import threading

class ClientePrueba:
    def __init__(self, host='localhost', puerto=9001):
        self.host = host
        self.puerto = puerto
    
    def conectar(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.puerto))
            print(f"Conectado al servidor en {self.host}:{self.puerto}")
            return True
        except Exception as e:
            print(f"Error conectando: {e}")
            return False
    
    def subir_archivo(self, nombre_archivo, datos):
        datos_b64 = base64.b64encode(datos).decode('utf-8')
        mensaje = {
            'comando': 'SUBIR_ARCHIVO',
            'nombre_archivo': nombre_archivo,
            'datos': datos_b64
        }
        
        self.sock.send(json.dumps(mensaje).encode())
        respuesta = self.sock.recv(4096)
        return json.loads(respuesta.decode())
    
    def listar_archivos(self):
        mensaje = {'comando': 'LISTAR_ARCHIVOS'}
        self.sock.send(json.dumps(mensaje).encode())
        respuesta = self.sock.recv(4096)
        return json.loads(respuesta.decode())
    
    def descargar_archivo(self, archivo_id):
        mensaje = {
            'comando': 'DESCARGAR_ARCHIVO',
            'archivo_id': archivo_id
        }
        self.sock.send(json.dumps(mensaje).encode())
        respuesta = self.sock.recv(1024 * 1024)  # 1MB buffer
        return json.loads(respuesta.decode())

def probar_servidor_1():
    print("=== PRUEBA SERVIDOR 1 (Puerto 9001) ===")
    cliente = ClientePrueba('localhost', 9001)
    
    if cliente.conectar():
        # Subir archivo de prueba
        datos_prueba = b"Este es un archivo de prueba para el sistema distribuido. " * 100  # ~5KB
        print(f"Subiendo archivo de {len(datos_prueba)} bytes...")
        
        resultado = cliente.subir_archivo("prueba.txt", datos_prueba)
        print("Resultado subida:", resultado)
        
        if resultado['estado'] == 'ok':
            archivo_id = resultado['archivo_id']
            print(f"Archivo ID: {archivo_id}")
            print(f"Bloques asignados: {resultado['bloques_asignados']}")
            
            # Listar archivos
            time.sleep(2)  # Esperar a que se propague
            lista = cliente.listar_archivos()
            print("Archivos en sistema:", lista)
            
            # Descargar archivo
            time.sleep(1)
            descarga = cliente.descargar_archivo(archivo_id)
            if descarga['estado'] == 'ok':
                datos_descargados = base64.b64decode(descarga['datos'])
                print(f"Descarga exitosa: {len(datos_descargados)} bytes")
                print(f"Integridad: {'OK' if datos_descargados == datos_prueba else 'ERROR'}")
            else:
                print("Error en descarga:", descarga)
        
        cliente.sock.close()

def probar_servidor_2():
    print("\n=== PRUEBA SERVIDOR 2 (Puerto 9002) ===")
    cliente = ClientePrueba('localhost', 9002)
    
    if cliente.conectar():
        # Listar archivos desde otro servidor
        time.sleep(3)
        lista = cliente.listar_archivos()
        print("Archivos visibles desde servidor 2:", lista)
        
        if lista['archivos']:
            # Intentar descargar desde servidor 2
            archivo_id = lista['archivos'][0]
            print(f"Descargando {archivo_id} desde servidor 2...")
            
            descarga = cliente.descargar_archivo(archivo_id)
            if descarga['estado'] == 'ok':
                datos = base64.b64decode(descarga['datos'])
                print(f"Descarga desde servidor 2: {len(datos)} bytes")
            else:
                print("Error descargando desde servidor 2:", descarga)
        
        cliente.sock.close()

def verificar_distribucion():
    print("\n=== VERIFICANDO DISTRIBUCION DE BLOQUES ===")
    time.sleep(2)
    
    # Verificar qué bloques hay en cada servidor
    for puerto in [8001, 8002, 8003]:
        blocks_dir = f"blocks_{puerto}"
        if os.path.exists(blocks_dir):
            bloques = os.listdir(blocks_dir)
            print(f"Servidor {puerto}: {len(bloques)} bloques")
            for bloque in bloques[:3]:  # Mostrar primeros 3
                print(f"  - {bloque}")
        else:
            print(f"Servidor {puerto}: directorio no existe")

if __name__ == "__main__":
    import os
    import sys
    
    # Agregar el directorio actual al path para importar
    sys.path.append('.')
    
    print("INICIANDO PRUEBA DEL SISTEMA DISTRIBUIDO")
    print("Asegurate de tener los 3 servidores ejecutandose...")
    print("Ejecuta en terminales separadas:")
    print("  python servidor1.py")
    print("  python servidor2.py") 
    print("  python servidor3.py")
    print("\nEsperando 5 segundos para que los servidores se conecten...")
    time.sleep(5)
    
    # Ejecutar pruebas
    probar_servidor_1()
    probar_servidor_2()
    verificar_distribucion()