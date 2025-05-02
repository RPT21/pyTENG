import sys
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication

"""
Data Classes (all subclasses of QGraphicsItem):
    PlotCurveItem - Displays a plot line given x,y data
    ScatterPlotItem - Displays points given x,y data
    PlotDataItem - Combines PlotCurveItem and ScatterPlotItem.
"""

# Crear la aplicación
app = QApplication(sys.argv)

# Crear la ventana principal
win = pg.GraphicsLayoutWidget(title="Ejemplo de diferencias")
win.show()
win.setWindowTitle('Ejemplo: plot(), PlotDataItem y PlotCurveItem')

# Crear un gráfico
# Recordem que el GraphicsLayoutWidget ens permet fer multi-panel de diferent contingut com gràfics, imatges, etc.
# En aquest cas plot1 és un únic plotItem que afegim i ocupa tota la pantalla en row=0, col=0.
plot1 = win.addPlot(title="Ejemplo Comparativo", row=0, col=0)

# Datos a graficar
x = np.linspace(0, 10, 100)
sin = np.sin(x)
cos = np.cos(x)
cos2 = 1 + np.cos(x)
sin2 = 1 + np.sin(x)

# --- Usando plot() --- Pintamos una curva sin crear una instancia de ella
plot1.plot(x, sin, pen='r', name="plot()")  # Dibuja una curva roja, no crea una instancia de la curva

# --- Usando PlotCurveItem() --- Pintamos una curva creando esta vez una instancia de ella
curve_item = pg.PlotCurveItem(x, sin2, pen='b', name="PlotCurveItem")
plot1.addItem(curve_item)  # Añade una curva azul (sin símbolos)

# --- Usando ScatterPlotItem() --- Pintamos una curva de puntos (sin línea)
scatter_item = pg.ScatterPlotItem(x, cos2, pen='w', name="PlotCurveItem")
plot1.addItem(scatter_item)  # Añade una curva de puntos blanca (no line)

# --- Usando PlotDataItem() --- Pintamos una curva de puntos con una línea que los atraviesa (ambas cosas a la vez)
data_item = pg.PlotDataItem(x, cos, pen='g', symbol='o', name="PlotDataItem")
plot1.addItem(data_item)  # Añade un PlotDataItem con símbolos 'o' (puntos dispersos) y línea verde


# Añadir leyenda
plot1.addLegend()

# Ejecutar la aplicación
sys.exit(app.exec_())
