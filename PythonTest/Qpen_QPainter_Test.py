import sys
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt

# Example of using QPainter to paint lines in the screen. We use QPen to customize the lines

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ejemplo de QPen y QPainter")
        self.resize(400, 300)

    def paintEvent(self, event):
        painter = QPainter(self)

        # Línea 1: roja, gruesa, sólida
        pen1 = QPen(QColor(255, 0, 0), 4, Qt.SolidLine)
        painter.setPen(pen1)
        painter.drawLine(50, 50, 350, 50)

        # Línea 2: verde, fina, discontinua
        pen2 = QPen(QColor(0, 255, 0), 2, Qt.DashLine)
        painter.setPen(pen2)
        painter.drawLine(50, 100, 350, 100)

        # Línea 3: azul, gruesa, punteada, con extremos redondeados
        pen3 = QPen(QColor(0, 0, 255), 5, Qt.DotLine)
        pen3.setCapStyle(Qt.RoundCap)
        painter.setPen(pen3)
        painter.drawLine(50, 150, 350, 150)

        # Línea 4: negra, estilo DashDotLine
        pen4 = QPen(Qt.black, 3, Qt.DashDotLine)
        painter.setPen(pen4)
        painter.drawLine(50, 200, 350, 200)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWidget()
    window.show()
    sys.exit(app.exec_())
