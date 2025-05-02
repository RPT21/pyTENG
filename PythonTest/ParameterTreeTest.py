import sys
from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

class ParameterTreeWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Parameter Tree Desplegable")
        self.setGeometry(100, 100, 600, 400)

        # Crear el layout y el widget principal
        layout = QVBoxLayout()
        self.widget = QWidget()
        self.widget.setLayout(layout)
        self.setCentralWidget(self.widget)

        # Crear los parámetros
        self.parameters = [
            {'name': 'Parámetro 1', 'type': 'float', 'value': 1.0, 'step': 0.1},
            {'name': 'Parámetro 2', 'type': 'int', 'value': 5, 'limits': (0, 10)},
            {'name': 'Parámetro 3', 'type': 'bool', 'value': True},
            {'name': 'Parámetro 4', 'type': 'float', 'value': 3.14, 'step': 0.01},
            {'name': 'Grupo 1', 'type': 'group', 'children': [
                {'name': 'Sub parámetro 1', 'type': 'int', 'value': 10},
                {'name': 'Sub parámetro 2', 'type': 'float', 'value': 0.5},
            ]},
            {'name': 'Grupo 2', 'type': 'group', 'children': [
                {'name': 'Sub parámetro 3', 'type': 'bool', 'value': False},
                {'name': 'Sub parámetro 4', 'type': 'float', 'value': 2.71},
            ]}
        ]

        # Crear la estructura de parámetros
        self.param_tree = Parameter.create(name='params', type='group', children=[
            param if param['type'] == 'group' else
            Parameter.create(name=param['name'], type=param['type'], value=param.get('value', None), **{k: v for k, v in param.items() if k not in ['name', 'type', 'value']})
            for param in self.parameters
        ])

        # Crear el widget del ParameterTree
        self.tree = ParameterTree()
        self.tree.setParameters(self.param_tree, showTop=False)

        # Agregar el ParameterTree al layout
        layout.addWidget(self.tree)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ParameterTreeWindow()
    window.show()
    sys.exit(app.exec_())
