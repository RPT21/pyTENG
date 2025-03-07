import sys
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt


class GraphWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana
        self.setWindowTitle("Gráfica Interactiva con Desplegable")
        self.setGeometry(100, 100, 800, 600)

        # Crear el widget de la gráfica
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')  # Fondo blanco
        self.graphWidget.setLabel('left', 'Amplitud', color='black', size='12pt')
        self.graphWidget.setLabel('bottom', 'Tiempo', color='black', size='12pt')

        # Crear el ComboBox (desplegable)
        self.comboBox = QComboBox()
        self.comboBox.addItem("Seno")
        self.comboBox.addItem("Coseno")
        self.comboBox.addItem("Tangente")

        # Conectar el evento de cambio de selección del comboBox
        self.comboBox.currentIndexChanged.connect(self.update_plot)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.comboBox)
        layout.addWidget(self.graphWidget)

        # Widget principal
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Inicializar los datos de la gráfica
        self.x = np.linspace(0, 2 * np.pi, 1000)
        self.y = np.sin(self.x)  # Función inicial
        self.plot = self.graphWidget.plot(self.x, self.y, pen=pg.mkPen(color='b', width=2))

    def update_plot(self):
        # Cambiar la función según la selección en el comboBox
        selection = self.comboBox.currentText()
        if selection == "Seno":
            self.y = np.sin(self.x)
        elif selection == "Coseno":
            self.y = np.cos(self.x)
        elif selection == "Tangente":
            self.y = np.tan(self.x)
            # Limitar los valores de tangente para evitar saltos grandes
            self.y = np.clip(self.y, -10, 10)

        # Actualizar la gráfica
        self.plot.setData(self.x, self.y)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GraphWindow()
    window.show()
    sys.exit(app.exec_())
