from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from PyQt5.QtWidgets import QApplication, QMainWindow

app = QApplication([])

# Creem un `GroupParameter` amb alguns paràmetres dins
group = GroupParameter(name="Configuració", children=[
    {'name': 'Velocitat', 'type': 'int', 'value': 10, 'limits': (0, 100)},
    {'name': 'Mode', 'type': 'list', 'values': ['Automàtic', 'Manual'], 'value': 'Manual'},
    {'name': 'Activat', 'type': 'bool', 'value': True}
])

# Creem el `ParameterTree` i afegim el grup
tree = ParameterTree()
tree.setParameters(group, showTop=False)

# Creem una finestra per mostrar-lo
window = QMainWindow()
window.setCentralWidget(tree)
window.resize(300, 400)
window.show()

app.exec_()
