# Sistema de Archivos Distribuido (DFS)

Este proyecto implementa un Sistema de Archivos Distribuido (DFS) en Python. Permite a los usuarios subir, descargar, eliminar y listar archivos que son almacenados de forma distribuida entre múltiples nodos de almacenamiento, todo gestionado por un servidor central de metadatos.

## Arquitectura

El sistema consta de tres componentes principales:

1.  **Servidor de Metadatos (Server)**: 
    -   Gestiona la tabla de archivos y directorios.
    -   Controla la ubicación de los bloques de datos.
    -   Monitorea el estado de los nodos de almacenamiento.
    -   Punto de entrada: `server_main.py`
    -   Puerto por defecto: 8001

2.  **Nodos de Almacenamiento (Storage Nodes)**: 
    -   Almacenan los bloques de datos físicos.
    -   Gestionan el espacio de almacenamiento local.
    -   Se pueden ejecutar múltiples nodos para aumentar la capacidad y redundancia.
    -   Punto de entrada: `node_main.py`
    -   Puerto por defecto: 8002 (configurable)

3.  **Cliente (Client)**: 
    -   Proporciona una interfaz gráfica (GUI) amigable.
    -   Permite subir, descargar, eliminar y visualizar archivos.
    -   Punto de entrada: `client_main.py`

## Requisitos Previos

-   Python 3.8 o superior
-   PyQt6 (para la interfaz gráfica del cliente)

Puedes instalar las dependencias necesarias con:

```bash
pip install PyQt6
```

## Ejecución del Sistema

Para probar el sistema localmente, se recomienda abrir tres terminales diferentes y ejecutar los componentes en el siguiente orden:

### 1. Iniciar el Servidor

El servidor es el coordinador del sistema y debe iniciarse primero.

```bash
python server_main.py
```

*Al iniciar, el servidor te guiará para configurar los nodos de almacenamiento si es la primera vez que se ejecuta.*

### 2. Iniciar Nodos de Almacenamiento

Ejecuta al menos un nodo de almacenamiento. Para un sistema redundante, se recomienda ejecutar al menos 2 o 3 nodos (en terminales separadas con puertos distintos, ej: 8002, 8003).

```bash
python node_main.py
```

*Sigue las instrucciones en pantalla para asignar un puerto y capacidad a cada nodo.*

### 3. Iniciar el Cliente

Finalmente, inicia la aplicación cliente para interactuar con el sistema.

```bash
python client_main.py
```

## Estructura del Proyecto

```
dfs
├─ client/          # Código fuente del cliente y GUI
├─ server/          # Código del servidor y gestión de metadatos
├─ nodes/           # Lógica de los nodos de almacenamiento
├─ core/            # Utilidades compartidas (protocolo, logger)
├─ server_main.py   # Script de inicio del servidor
├─ node_main.py     # Script de inicio de nodos
└─ client_main.py   # Script de inicio del cliente
```
