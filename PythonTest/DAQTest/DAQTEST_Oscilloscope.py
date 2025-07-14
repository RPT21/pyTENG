import sys
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg
import math


class Oscilloscope(QtWidgets.QMainWindow):
    def __init__(self, buffer_size=1000):
        super().__init__()
        self.setWindowTitle("Osciloscopio")

        # Configuración del buffer circular
        self.buffer_size = buffer_size
        self.buffer = np.zeros(buffer_size, dtype=float)
        self.write_index = 0

        # Gráfica de PyQtGraph
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.curve = self.plot_widget.plot(pen='y')
        self.plot_widget.setYRange(-1.2, 1.2)

        # Timer para simular adquisición de datos
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(10)  # ms

        # Simulación: frecuencia y fase de la señal
        self.t = 0
        self.freq = 2  # Hz

    def update(self):
        # Simular un nuevo dato (senoidal)
        new_sample = math.sin(2 * math.pi * self.freq * self.t)
        self.t += 0.01

        # Escribir en el buffer circular
        self.buffer[self.write_index] = new_sample
        self.write_index = (self.write_index + 1) % self.buffer_size

        # Mostrar la señal "moviéndose" a la izquierda
        display_data = np.concatenate((
            self.buffer[self.write_index:],
            self.buffer[:self.write_index]
        ))
        self.curve.setData(display_data)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    osc = Oscilloscope()
    osc.show()
    sys.exit(app.exec_())
