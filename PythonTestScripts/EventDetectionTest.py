import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QGroupBox
from pyqtgraph.parametertree import Parameter, ParameterTree

class DynamicParameterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ventana Dinámica con ParameterTrees y Cambio Detectado")
        self.setGeometry(100, 100, 800, 600)

        # Widget central y layout principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Botón para añadir bloques dinámicos
        self.add_block_button = QPushButton("Añadir Bloque de Parámetros")
        self.add_block_button.clicked.connect(self.add_parameter_block)
        self.main_layout.addWidget(self.add_block_button)

        # Contenedor para los bloques de parámetros
        self.blocks_layout = QVBoxLayout()
        self.main_layout.addLayout(self.blocks_layout)

        # Contador de bloques para nombres únicos
        self.block_counter = 1

    def add_parameter_block(self):
        """Crea un nuevo bloque de parámetros y lo añade al layout."""
        block_name = f'Bloque {self.block_counter}'
        self.block_counter += 1

        # Crear el groupbox contenedor
        group_box = QGroupBox(block_name)
        group_box_layout = QVBoxLayout()
        group_box.setLayout(group_box_layout)

        # Crear el ParameterTree y registrar cambios
        parameter_tree, parameter_root = self.create_parameter_tree(block_name)
        group_box_layout.addWidget(parameter_tree)

        # Conectar eventos de cambio
        self.register_callbacks(parameter_root, block_name)

        # Añadir el bloque al layout
        self.blocks_layout.addWidget(group_box)

    def create_parameter_tree(self, block_name):
        """Crea un ParameterTree con un grupo de parámetros."""
        parameters = [
            {'name': 'Configuración', 'type': 'group', 'children': [
                {'name': 'Parámetro 1', 'type': 'float', 'value': 1.0},
                {'name': 'Parámetro 2', 'type': 'bool', 'value': True},
                {'name': 'Modo', 'type': 'list', 'values': ['Normal', 'Avanzado', 'Experto'], 'value': 'Normal'},
                {'name': 'Subgrupo', 'type': 'group', 'children': [
                    {'name': 'Subparámetro 1', 'type': 'int', 'value': 10},
                    {'name': 'Subparámetro 2', 'type': 'float', 'value': 3.14},
                ]}
            ]}
        ]

        parameter_root = Parameter.create(name=f'{block_name} Parameters', type='group', children=parameters)
        parameter_tree = ParameterTree()
        parameter_tree.setParameters(parameter_root, showTop=False)

        return parameter_tree, parameter_root

    def register_callbacks(self, param_group, block_name):
        """Recorre todos los parámetros y conecta sigValueChanged para imprimir cambios."""
        for param in param_group.children():
            self.register_recursive_callbacks(param, block_name)

    def register_recursive_callbacks(self, param, block_name):
        """Registra la señal sigValueChanged para un parámetro y sus hijos."""
        param.sigValueChanged.connect(lambda param, value: self.parameter_changed(param, value, block_name))

        if param.type() == 'group':
            for child in param.children():
                self.register_recursive_callbacks(child, block_name)

    def parameter_changed(self, param, value, block_name):
        """Función que se llama cuando un parámetro cambia."""
        print(f"[{block_name}] '{param.name()}' cambió a: {value}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DynamicParameterWindow()
    window.show()
    sys.exit(app.exec_())
