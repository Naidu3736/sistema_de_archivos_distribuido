

'''# **--- Configuración de Red ---

# !! IMPORTANTE !!
# Reemplaza estas IPs con las IPs reales de tus máquinas
IP_PC_1 = "192.168.1.12"  # <-- Pon la IP de tu PC 1 aquí
IP_PC_2 = "192.168.1.12"  # <-- Pon la IP de tu PC 2 aquí

# Lista de todos los nodos en el sistema
# Puedes correr solo 2 nodos (uno en cada PC) o los 4 (dos en cada PC)

NODOS_CONOCIDOS = {
    # Nodos en PC 1
    'nodo1': (IP_PC_1, 50001),
    'nodo2': (IP_PC_1, 50002),
    
    # Nodos en PC 2
    #'nodo3': (IP_PC_1, 50003),
    #'nodo4': (IP_PC_1, 50004),
}


# --- Configuración del Sistema de Archivos ---
BLOCK_SIZE = 1024 * 1024 
LOCAL_STORAGE_CAPACITY_MB = 75 
LOCAL_STORAGE_DIR = "Espacio_Compartido" '''

# Config.py (Versión de 2 Nodos)

# --- Configuración de Red ---

# Usar '127.0.0.1' (localhost) para probar todo en una PC
IP_BASE = "127.0.0.1" 

# Lista de todos los nodos en el sistema (ahora solo 2)
NODOS_CONOCIDOS = {
    'nodo1': (IP_BASE, 50001), # Nodo Base
    'nodo2': (IP_BASE, 50002), # Nodo Cliente
}

# --- Configuración del Sistema de Archivos ---
BLOCK_SIZE = 1024 * 1024 
LOCAL_STORAGE_CAPACITY_MB = 75 
LOCAL_STORAGE_DIR = "Espacio_Compartido"