
SADTF - Sistema de Archivos Distribuido Tolerante a Fallas
Este proyecto es una simulación de un Sistema de Archivos Distribuido Tolerante a Fallas (SADTF) desarrollado en Python para el curso de Sistemas Operativos II. Utiliza PyQt5 para la interfaz gráfica y sockets de Python para la comunicación de red entre nodos.

El sistema permite almacenar archivos grandes dividiéndolos en bloques de 1 Mbyte y replicando cada bloque para asegurar la tolerancia a fallas.


Características Principales

-Particionamiento de Archivos: Los archivos se dividen en bloques de 1 Mbyte.

-Tolerancia a Fallas: Cada bloque se replica (guarda una copia) en un nodo diferente. Si el nodo original falla, el sistema recupera el bloque desde su copia.

-Gestión de Metadatos: Utiliza una "Tabla de Bloques" (similar a la paginación) que se sincroniza entre todos los nodos para saber dónde está cada bloque y su copia.

-Interfaz Gráfica Sincronizada: Todos los nodos comparten la misma vista del sistema de archivos.

Operaciones del Sistema:

Guardar (Subir): Particiona un archivo y distribuye sus bloques y copias en la red.


Descargar: Reconstruye un archivo solicitando los bloques a los nodos (usando la copia si es necesario).


Eliminar: Borra un archivo, marcando sus entradas en la tabla como libres y eliminando los bloques de los nodos remotos.


Atributos: Muestra la ubicación de cada bloque y su copia.


Tabla: Muestra el contenido de la "Tabla de Bloques".

Arquitectura
El sistema está construido con 4 archivos principal

-Main: El punto de entrada principal. Contiene la lógica de la GUI (PyQt) y coordina las operaciones.

network.py: Contiene la lógica de red:

DFSServerThread: El servidor (en un hilo QThread) que escucha peticiones de otros nodos.

DFSClient: El cliente que envía peticiones (subir/descargar bloques, actualizar metadatos).

sadtf_utils.py: Contiene la lógica de negocio:

MetadataManager: La clase que gestiona la "Tabla de Bloques" y el estado del sistema.

particionar_archivo / combinar_bloques: Funciones para dividir y reconstruir archivos.

sadtf_config.py: Define la configuración de la red (IPs y puertos de los nodos) y el tamaño de los bloques.

🛠️ Instalación y Dependencias
El proyecto solo requiere Python 3 y la biblioteca PyQt5.

Asegúrate de tener Python 3 instalado.

Instala PyQt5 usando pip:

Bash

pip install PyQt5
🚀 Cómo Ejecutar la Simulación (4 Nodos en 1 PC)
Para probar el sistema distribuido en una sola máquina, simularemos los 4 nodos ejecutando 4 instancias del programa en 4 puertos diferentes (como se define en sadtf_config.py).

Guarda los 4 archivos (sadtf_config.py, sadtf_utils.py, sadtf_network.py, sadtf_main_app.py) en la misma carpeta.

Abre 4 ventanas de Terminal (o PowerShell/CMD) diferentes.

En cada terminal, navega a la carpeta donde guardaste los archivos.

Ejecuta un nodo diferente en cada terminal, especificando su puerto:

Terminal 1 (Nodo 1):

Bash

python sadtf_main_app.py 50001
Terminal 2 (Nodo 2):

Bash

python sadtf_main_app.py 50002
Terminal 3 (Nodo 3):

Bash

python sadtf_main_app.py 50003
Terminal 4 (Nodo 4):

Bash

python sadtf_main_app.py 50004
Probando el Sistema
Verás 4 ventanas de la aplicación abiertas, cada una representando un nodo.

Subir: Usa el botón "Guardar (Subir)" en cualquiera de las ventanas. Una vez que el archivo se suba, la lista de archivos se actualizará automáticamente en las otras 3 ventanas.

Probar Tolerancia a Fallas: Sube un archivo. Luego, cierra una de las terminales (simulando una falla de nodo). Ve a otra ventana y usa el botón "Descargar" para ese archivo. El sistema deberá recuperarlo exitosamente usando las copias replicadas.

Almacenamiento: Se crearán carpetas locales para cada nodo (ej. Espacio_Compartido_50001, Espacio_Compartido_50002, etc.) donde podrás ver los bloques de 1MB almacenados.