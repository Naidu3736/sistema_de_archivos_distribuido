import socket
import os
from core.split_union import split

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("192.168.101.9", 8001))
server.listen(5)

client, addr = server.accept()

block_dir = "blocks"

# Recibir metadata
size_bytes = client.recv(4)
size = int.from_bytes(size_bytes, 'big')
file_bytes = client.recv(size)
file = file_bytes.decode('utf-8')

dir_temp = "temp"
os.makedirs(dir_temp, exist_ok=True)
file_temp_path = os.path.join(dir_temp, file)

file_size_bytes = client.recv(8)
file_size = int.from_bytes(file_size_bytes, 'big')

with open(file_temp_path, 'wb') as f:
    bytes_received = 0
    while bytes_received < file_size:
        print(f"Estado de carga: {bytes_received}B / {file_size}B")
        chunk = client.recv(min(4096, file_size - bytes_received))
        f.write(chunk)
        bytes_received += len(chunk)

filename = os.path.splitext(file)[0]
sub_dir = filename
sub_dir_path = os.path.join(block_dir, sub_dir)
blocks = split(file_path=file_temp_path, output_dir=sub_dir_path)

os.remove(file_temp_path)
os.rmdir(dir_temp)

# Enviar metadata
sub_dir_bytes = sub_dir.encode('utf-8')
client.send(len(sub_dir_bytes).to_bytes(4, 'big'))
client.send(sub_dir_bytes)  

filename_bytes = filename.encode('utf-8')
client.send(len(filename_bytes).to_bytes(4, 'big'))
client.send(filename_bytes)

# Enviar número de bloques
client.send(len(blocks).to_bytes(4, 'big'))

# Enviar cada bloque con separación clara
for block in blocks:
    # Enviar nombre del bloque
    block_name_bytes = block.encode('utf-8')
    client.send(len(block_name_bytes).to_bytes(4, 'big'))
    client.send(block_name_bytes)

    # Enviar tamaño del bloque
    block_path = f"blocks/{sub_dir}/{block}"
    block_size = os.path.getsize(block_path)
    client.send(block_size.to_bytes(8, 'big'))  # 8 bytes para tamaño

    # Enviar contenido del bloque
    with open(block_path, 'rb') as f:
        bytes_sent = 0
        while bytes_sent < block_size:
            chunk = f.read(4096)
            client.send(chunk)
            bytes_sent += len(chunk)

    print(f"Bloque {block} enviado ({block_size} bytes)")

print("Todos los bloques enviados")
client.close()
server.close()