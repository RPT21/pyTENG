class A:
    def metodo(self):
        print("Método de A")

class B(A):
    def metodo(self):
        super(B, self).metodo()  # A partir de B, busca la superclasse, y executa metodo()
        print("Método de B")

class C(B):
    def metodo(self):
        super(B, self).metodo()  # A partir de B, busca la superclasse, y executa metodo()
        print("Método de C")

# super(B, self) el que fa es, partint de la classe B, busca la superclasse
# de la qual hereda, i executa el mètode metodo().
C().metodo()

