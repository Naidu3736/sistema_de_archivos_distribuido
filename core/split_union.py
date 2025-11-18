# split_union.py
import os

SIZE_BUFFER = 4096  # 4KB por chunk
BLOCK_SIZE = 1024 * 1024  # 1MB por bloque

def split(file_path: str, output_dir: str = "blocks") -> list:
    """
    Divide un archivo en bloques de 1MB
    Retorna: lista con los nombres de los archivos de bloque creados
    """
    # Crear directorio de bloques si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    block_files = []  # Lista para guardar nombres de bloques
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    try:
        with open(file_path, "rb") as file_in:
            current_part = 0
            bytes_written = 0
            current_block_data = b''
            
            while True:
                chunk = file_in.read(SIZE_BUFFER)
                if not chunk:  # Fin del archivo
                    break
                
                # Si agregar este chunk excede el tamaño del bloque
                if len(current_block_data) + len(chunk) > BLOCK_SIZE:
                    # Guardar bloque actual
                    block_filename = f"block_{current_part}.bin"
                    block_filepath = os.path.join(output_dir, block_filename)
                    
                    with open(block_filepath, "wb") as block_file:
                        block_file.write(current_block_data)
                    
                    block_files.append(block_filename)
                    
                    # Preparar siguiente bloque
                    current_part += 1
                    current_block_data = b''
                    bytes_written = 0
                
                # Agregar chunk al bloque actual
                current_block_data += chunk
                bytes_written += len(chunk)
            
            # Guardar el último bloque si queda data
            if current_block_data:
                block_filename = f"block_{current_part}.bin"
                block_filepath = os.path.join(output_dir, block_filename)
                
                with open(block_filepath, "wb") as block_file:
                    block_file.write(current_block_data)
                
                block_files.append(block_filename)
            
            print(f"Archivo dividido en {len(block_files)} bloques")
            return block_files
            
    except Exception as e:
        print(f"Error dividiendo archivo: {e}")
        return []

def union(block_files: list, output_file: str, blocks_dir: str = "blocks"):
    """
    Reconstruye un archivo desde sus bloques
    """
    try:
        with open(output_file, "wb") as file_out:
            for block_filename in block_files:
                block_filepath = os.path.join(blocks_dir, block_filename)
                
                if not os.path.exists(block_filepath):
                    print(f"Bloque no encontrado: {block_filename}")
                    continue
                
                with open(block_filepath, "rb") as block_file:
                    while True:
                        chunk = block_file.read(SIZE_BUFFER)
                        if not chunk:
                            break
                        file_out.write(chunk)
            
        print(f"Archivo reconstruido: {output_file}")
        
    except Exception as e:
        print(f"Error reconstruyendo archivo: {e}")

def clean_blocks(block_files: list, blocks_dir: str = "blocks"):
    """
    Limpia los archivos de bloque temporales
    """
    for block_filename in block_files:
        block_filepath = os.path.join(blocks_dir, block_filename)
        if os.path.exists(block_filepath):
            os.remove(block_filepath)
    print("Bloques temporales eliminados")