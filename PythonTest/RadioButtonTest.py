import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from pyqtgraph.parametertree import Parameter, ParameterTree

class RadioButtonParameterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Lista de Booleans - Exclusivos")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        self.parameter_tree = ParameterTree()
        layout.addWidget(self.parameter_tree)

        self.create_parameters()

    def create_parameters(self):
        self.parameters = [
            {'name': 'Opción 1', 'type': 'bool', 'value': False},
            {'name': 'Opción 2', 'type': 'bool', 'value': False},
            {'name': 'Opción 3', 'type': 'bool', 'value': False},
            {'name': 'Opción 4', 'type': 'bool', 'value': False},
        ]

        self.root_param = Parameter.create(name='Opciones Exclusivas', type='group', children=self.parameters)
        self.parameter_tree.setParameters(self.root_param, showTop=False)

        # Conectar el cambio de cualquier parámetro a una función común
        for param in self.root_param.children():
            param.sigValueChanged.connect(self.handle_parameter_change)

    def handle_parameter_change(self, param, value):
        if value:
            # Si uno se activa (se pone en True), desactivar los demás
            for other_param in self.root_param.children():
                if other_param is not param:
                    other_param.setValue(False)

        print(f"{param.name()} cambiado a {value}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RadioButtonParameterWindow()
    window.show()
    sys.exit(app.exec_())
