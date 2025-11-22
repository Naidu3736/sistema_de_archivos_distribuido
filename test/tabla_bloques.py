class TablaBloques:
    def __init__(self, nodos):
        self.nodos = nodos
        self.capacidad_total = (sum(nodo['capacidad']) for nodo in nodos)
        self.tabla = [None] * self.capacidad_total
        self.bloques_libres = []
        self.bloques_ocupados = []

    def 