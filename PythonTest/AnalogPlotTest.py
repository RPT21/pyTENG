import sys
import numpy as np
from PyDAQmx import Task
from PyDAQmx.DAQmxTypes import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *
from ctypes import byref

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
import pyqtgraph as pg

class DAQSignal(QObject):
    data_ready = pyqtSignal(np.ndarray)

class DAQTask(Task):
    def __init__(self, signal, sample_rate=1000, samples_per_chunk=100):
        super().__init__()
        self.signal = signal
        self.sample_rate = sample_rate
        self.samples_per_chunk = samples_per_chunk

        self.buffer = np.zeros(samples_per_chunk, dtype=np.float64)

        self.CreateAIVoltageChan("Dev1/ai0", "", DAQmx_Val_Cfg_Default, -10.0, 10.0,
                                 DAQmx_Val_Volts, None)
        self.CfgSampClkTiming("", sample_rate, DAQmx_Val_Rising,
                              DAQmx_Val_ContSamps, samples_per_chunk)

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

        self.signal = DAQSignal()
        self.signal.data_ready.connect(self.update_plot)

        self.daq = DAQTask(self.signal, sample_rate=1000, samples_per_chunk=100)
        self.daq.Start()

    def update_plot(self, new_data):
        self.data = np.roll(self.data, -len(new_data))
        self.data[-len(new_data):] = new_data
        self.curve.setData(self.data)

    def closeEvent(self, event):
        self.daq.Stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(800, 400)
    win.show()
    sys.exit(app.exec_())
