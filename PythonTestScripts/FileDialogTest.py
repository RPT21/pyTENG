import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog
from pyqtgraph.parametertree import Parameter, ParameterTree

class FileSelectorExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Selector de Ficheros")
        self.setGeometry(100, 100, 500, 300)

        self.file_path = ""  # Aquí guardaremos el path seleccionado

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        self.parameter_tree = ParameterTree()
        layout.addWidget(self.parameter_tree)

        self.setup_parameters()

        # Botón para abrir el diálogo
        self.select_file_button = QPushButton("Seleccionar Fichero")
        self.select_file_button.clicked.connect(self.open_file_dialog)

        layout.addWidget(self.select_file_button)

        central_widget.setLayout(layout)

    def setup_parameters(self):
        # Parámetro donde guardaremos el path
        params = [
            {'name': 'Ruta del Fichero', 'type': 'str', 'value': '', 'readonly': True},
        ]

        self.root_param = Parameter.create(name='Configuración', type='group', children=params)
        self.parameter_tree.setParameters(self.root_param, showTop=False)

    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo", "", "Todos los archivos (*)", options=options)

        if file_path:  # Si seleccionó un archivo
            self.file_path = file_path
            print(f"Archivo seleccionado: {file_path}")
            self.root_param.param('Ruta del Fichero').setValue(file_path)  # Actualizamos en el parameter tree

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FileSelectorExample()
    window.show()
    sys.exit(app.exec_())
