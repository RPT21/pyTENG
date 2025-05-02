import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import sys

# Crear una aplicación Qt
app = QtWidgets.QApplication(sys.argv)

# Crear una ventana con un widget de gráficos
win = pg.GraphicsLayoutWidget(title="Ejemplo con mkPen")
win.resize(600, 400)
win.show()

# Añadir un gráfico
plot1 = win.addPlot(title="Línea con estilo personalizado")  # Afegim un plotItem

# Datos de ejemplo
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Crear un pen personalizado - Crea un objeto QPen de PyQt5 adaptado a PyQtGraph para personalizar el trazado de curvas
# Con esto podemos personalizar el color, grosor, linestyle, etc...
# mkPen() nos permite customizar el trazado de una curva en GraphicsLayoutWidget
pen = pg.mkPen(color=(255, 0, 0), width=2, style=QtCore.Qt.DashLine)

# Dibujar la curva con el pen personalizado
plot1.plot(x, y, pen=pen, name="Seno")

# Ejecutar la aplicación
sys.exit(app.exec_())
