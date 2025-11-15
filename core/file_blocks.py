import os
import time

SIZE_BUFFER = 4096

def split(file : str, size_block : int = 1024 * 1024):
    with open(file, "rb") as file_in:
        file_name = os.path.splitext(os.path.basename(file))[0]
        
        current_part = 0
        bytes_write = 0
        
        with open(f"{file_name}_part_{current_part}.bin", "wb") as file_out:
            chunk = file_in.read(SIZE_BUFFER)

            while len(chunk) > 0:
                if len(chunk) + bytes_write > size_block and bytes_write > 0:
                    file_out.close()
                    current_part += 1
                    file_out = open(f"{file_name}_part_{current_part}.bin", "wb")
                    bytes_write = 0

                file_out.write(chunk)
                bytes_write += len(chunk)

                chunk = file_in.read(SIZE_BUFFER)

        file_out.close()


def union(file : str):
    with open(file, "wb") as file_out:
        i = 0
        file_name = os.path.splitext(os.path.basename(file))[0]
        while True:
            part_file_name = f"{file_name}_part_{i}.bin"

            if not os.path.exists(part_file_name):
                break

            with open(part_file_name, "rb") as file_in:
                chunk = file_in.read(SIZE_BUFFER)

                while len(chunk) > 0:
                    file_out.write(chunk)
                    chunk = file_in.read(SIZE_BUFFER)

                i += 1

                file_in.close()

        file_out.close()



size_block = int(input("Ingrese el tamano de bloque: "))
split("./ellen.mp4", size_block=size_block)
input("Presione una tecla...")
union("./ellen.mp4")