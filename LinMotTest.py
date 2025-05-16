import sys
import numpy as np
from PyDAQmx import Task
from PyDAQmx.DAQmxTypes import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *
from ctypes import byref

from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
import pyqtgraph as pg
import threading

from PyDAQmx import DAQmxResetDevice

DAQmxResetDevice("Dev1")

moveLinMot = False


class DAQSignal(QObject):
    data_ready = pyqtSignal(np.ndarray)


class DAQTask(Task):
    def __init__(self, signal, sample_rate=1000, samples_per_chunk=100):
        super().__init__()
        self.signal = signal
        self.sample_rate = sample_rate
        self.samples_per_chunk = samples_per_chunk

        self.buffer = np.zeros(samples_per_chunk, dtype=np.float64)

        self.CreateAIVoltageChan("Dev1/ai2", "", DAQmx_Val_RSE, -10.0, 10.0, DAQmx_Val_Volts, None)
        self.CfgSampClkTiming("", sample_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, samples_per_chunk)

        # Registrar callback
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, samples_per_chunk, 0)

    def Start(self):
        self.StartTask()

    def Stop(self):
        self.StopTask()
        self.ClearTask()

    def EveryNCallback(self):
        read = int32()
        self.ReadAnalogF64(self.samples_per_chunk, 10.0, DAQmx_Val_GroupByChannel,
                           self.buffer, self.samples_per_chunk, byref(read), None)
        self.signal.data_ready.emit(self.buffer.copy())
        return 0  # continuar ejecución


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyDAQmx Analog Real-Time Plot")
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.curve = self.plot_widget.plot(pen='g')
        self.data = np.zeros(1000)
        self.do_task = DigitalOutputTask()
        self.do_task.StartTask()

        self.signal = DAQSignal()
        self.signal.data_ready.connect(self.update_plot)

        self.daq = DAQTask(self.signal, sample_rate=1000, samples_per_chunk=100)
        self.daq.Start()

        # Botón para controlar linmot
        self.button = QPushButton("Encender LinMot", self)
        self.button.setGeometry(150, 150, 200, 40)
        self.button.clicked.connect(self.toggle_linmot)

    def update_plot(self, new_data):
        self.data = np.roll(self.data, -len(new_data))
        self.data[-len(new_data):] = new_data
        self.curve.setData(self.data)

    def toggle_linmot(self):
        global moveLinMot
        if moveLinMot:
            self.do_task.set_line(0)
        else:
            self.do_task.set_line(1)
        moveLinMot = not moveLinMot
        self.button.setText("Apagar LinMot" if moveLinMot else "Encender LinMot")

    def closeEvent(self, event):
        # Detener la tarea DAQ
        self.daq.Stop()
        event.accept()
        self.do_task.set_line(0)
        self.do_task.StopTask()
        self.do_task.ClearTask()


class DigitalOutputTask(Task):
    def __init__(self, line="Dev1/port0/line7"):
        Task.__init__(self)
        self.CreateDOChan(line, "", DAQmx_Val_ChanForAllLines)

    def set_line(self, value):
        """value = 0 (OFF) o 1 (ON)"""
        data = np.array([value], dtype=np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, DAQmx_Val_GroupByChannel, data, None, None)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(800, 400)
    win.show()
    sys.exit(app.exec_())
