from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree.parameterTypes import ColorParameter
from PyQt5.QtWidgets import QApplication, QMainWindow

app = QApplication([])

# Creem un ParameterTree (el widget visual)
tree = ParameterTree()

# Creem un paràmetre de tipus color
# param = Parameter.create(name="Color de fons", type="color", value=(255, 0, 0, 255))  # Color vermell RGBA

param = Parameter.create(name="Color de fons", type="color", value=(255, 0, 0, 255), children=[
    {'name': 'Intensitat', 'type': 'int', 'value': 50}
])

# Afegim el paràmetre al ParameterTree
tree.setParameters(param, showTop=True)

# Creem una finestra i afegim-hi l'arbre de paràmetres
window = QMainWindow()
window.setCentralWidget(tree)
window.show()

app.exec_()
