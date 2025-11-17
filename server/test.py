from server import Servidor

if __name__ == "__main__":
    servidor = Servidor(puerto=8001)
    servidor.iniciar()