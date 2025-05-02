import sys
from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGroupBox, QHBoxLayout, QLabel

class ParameterBlock(QWidget):
    """ Un bloque con un título y un ParameterTree dentro. """

    def __init__(self, title, parameters):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Título
        self.titleLabel = QLabel(f"<b>{title}</b>")
        self.layout.addWidget(self.titleLabel)

        # Crear ParameterTree y configurarlo
        self.param_tree = ParameterTree()

        # Crear la estructura de parámetros
        self.param_root = Parameter.create(name=f"{title} Params", type='group', children=parameters)
        self.param_tree.setParameters(self.param_root, showTop=False)

        self.layout.addWidget(self.param_tree)


class MultiBlockParameterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ventana con Múltiples Bloques de ParameterTrees")
        self.setGeometry(100, 100, 800, 600)

        # Layout principal
        mainLayout = QVBoxLayout()
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

        # Lista de bloques de parámetros
        block_definitions = [
            {
                'title': 'Bloque 1',
                'parameters': [
                    {'name': 'Parametro A1', 'type': 'float', 'value': 1.0},
                    {'name': 'Parametro A2', 'type': 'bool', 'value': True},
                    {'name': 'Subgrupo A', 'type': 'group', 'children': [
                        {'name': 'Subparametro A1', 'type': 'float', 'value': 2.0},
                        {'name': 'Subparametro A2', 'type': 'int', 'value': 5}
                    ]}
                ]
            },
            {
                'title': 'Bloque 2',
                'parameters': [
                    {'name': 'Parametro B1', 'type': 'float', 'value': 3.14},
                    {'name': 'Parametro B2', 'type': 'bool', 'value': False},
                    {'name': 'Subgrupo B', 'type': 'group', 'children': [
                        {'name': 'Subparametro B1', 'type': 'float', 'value': 0.5},
                        {'name': 'Subparametro B2', 'type': 'int', 'value': 10}
                    ]}
                ]
            }
        ]

        # Crear y añadir cada bloque al layout principal
        for block in block_definitions:
            groupBox = QGroupBox(block['title'])
            blockLayout = QVBoxLayout()
            groupBox.setLayout(blockLayout)

            # Crear el widget ParameterBlock y añadirlo al GroupBox
            parameterBlock = ParameterBlock(block['title'], block['parameters'])
            blockLayout.addWidget(parameterBlock)

            # Añadir cada groupbox al layout principal
            mainLayout.addWidget(groupBox)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MultiBlockParameterWindow()
    window.show()
    sys.exit(app.exec_())
