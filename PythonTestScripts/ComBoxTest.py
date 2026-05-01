import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton
from PyQt5.QtCore import Qt


class ParameterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ventana con Desplegables y Botón")
        self.setGeometry(100, 100, 400, 300)

        # Crear el layout para los widgets
        layout = QVBoxLayout()

        # Crear el ComboBox (desplegable) con opciones
        self.comboBox = QComboBox()
        self.comboBox.addItem("Opción 1")
        self.comboBox.addItem("Opción 2")
        self.comboBox.addItem("Opción 3")

        # Crear el botón
        self.button = QPushButton("Aceptar")
        self.button.clicked.connect(self.on_button_click)

        # Añadir el ComboBox y el botón al layout
        layout.addWidget(self.comboBox)
        layout.addWidget(self.button)

        # Crear el widget central y asignarle el layout
        centralWidget = QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)

    def on_button_click(self):
        # Obtener la opción seleccionada en el ComboBox
        selected_option = self.comboBox.currentText()
        print(f"Opción seleccionada: {selected_option}")
        # Aquí puedes hacer lo que desees con la opción seleccionada


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ParameterWindow()
    window.show()
    sys.exit(app.exec_())
