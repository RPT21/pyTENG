import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow
import pyqtgraph as pg

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ejemplo de pyqtgraph con GraphicsLayoutWidget")
        self.resize(800, 600)

        # Crear un widget de layout gráfico
        self.graphWidget = pg.GraphicsLayoutWidget(show=True)
        self.setCentralWidget(self.graphWidget)

        # Primer gráfico (fila 0, columna 0)
        plot1 = self.graphWidget.addPlot(title="Seno")
        x = np.linspace(0, 10, 1000)
        y = np.sin(x)
        plot1.plot(x, y, pen='r')

        # Segundo gráfico en la misma fila (columna 1)
        plot2 = self.graphWidget.addPlot(title="Coseno")
        y2 = np.cos(x)
        plot2.plot(x, y2, pen='g')

        # Ir a la siguiente fila
        self.graphWidget.nextRow()

        # Tercer gráfico en una nueva fila (columna 0)
        plot3 = self.graphWidget.addPlot(title="Seno + Ruido")
        y3 = np.sin(x) + np.random.normal(0, 0.1, size=len(x))
        plot3.plot(x, y3, pen='b')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
