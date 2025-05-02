import sys
from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

class ParameterTreeWithGroup(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ParameterTree con Grupo de Parámetros")
        self.setGeometry(100, 100, 600, 400)

        # Crear el layout principal
        layout = QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Definir un grupo de parámetros
        parameters = [
            {'name': 'Configuración General', 'type': 'group', 'children': [
                {'name': 'Tamaño', 'type': 'float', 'value': 10.0, 'step': 0.5},
                {'name': 'Activado', 'type': 'bool', 'value': True},
                {'name': 'Velocidad', 'type': 'float', 'value': 5.5},
                {'name': 'Modo', 'type': 'list', 'values': ['Normal', 'Avanzado', 'Experto'], 'value': 'Normal'},
            ]}
        ]

        # Crear el parámetro raíz (es un grupo global)
        self.param_root = Parameter.create(name='params', type='group', children=parameters)

        # Crear el árbol de parámetros
        self.tree = ParameterTree()
        self.tree.setParameters(self.param_root, showTop=False)

        # Añadir el árbol al layout
        layout.addWidget(self.tree)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ParameterTreeWithGroup()
    window.show()
    sys.exit(app.exec_())
