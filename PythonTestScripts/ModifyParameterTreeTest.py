import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QGroupBox
from pyqtgraph.parametertree import Parameter, ParameterTree

class DynamicParameterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Modificar ParameterTree")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        self.add_block_button = QPushButton("Añadir Bloque")
        self.add_block_button.clicked.connect(self.add_parameter_block)
        self.main_layout.addWidget(self.add_block_button)

        self.modify_button = QPushButton("Modificar Valores del Primer Bloque")
        self.modify_button.clicked.connect(self.modify_first_block)
        self.main_layout.addWidget(self.modify_button)

        self.blocks_layout = QVBoxLayout()
        self.main_layout.addLayout(self.blocks_layout)

        self.block_counter = 1
        self.parameter_roots = []  # Lista para guardar todos los grupos de parámetros

    def add_parameter_block(self):
        block_name = f'Bloque {self.block_counter}'
        self.block_counter += 1

        group_box = QGroupBox(block_name)
        group_box_layout = QVBoxLayout()
        group_box.setLayout(group_box_layout)

        parameter_tree, parameter_root = self.create_parameter_tree(block_name)
        self.parameter_roots.append(parameter_root)

        group_box_layout.addWidget(parameter_tree)

        self.blocks_layout.addWidget(group_box)

    def create_parameter_tree(self, block_name):
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

    def modify_first_block(self):
        if len(self.parameter_roots) == 0:
            print("No hay bloques para modificar.")
            return

        # Acceder al primer grupo de parámetros (Bloque 1)
        first_block = self.parameter_roots[0]

        # Cambiar valores de parámetros específicos
        first_block.child('Configuración', 'Parámetro 1').setValue(99.99)
        first_block.child('Configuración', 'Parámetro 2').setValue(False)
        first_block.child('Configuración', 'Modo').setValue('Experto')
        first_block.child('Configuración', 'Subgrupo', 'Subparámetro 1').setValue(500)
        first_block.child('Configuración', 'Subgrupo', 'Subparámetro 2').setValue(9.81)

        print("Parámetros del primer bloque actualizados.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DynamicParameterWindow()
    window.show()
    sys.exit(app.exec_())
