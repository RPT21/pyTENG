import sys
import numpy as np
import pandas as pd
import time
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
import pyqtgraph as pg
from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

# ---------------- CONFIG ----------------
CHANNEL = "Dev1/ai0"
SAMPLE_RATE = 1000
SAMPLES_PER_CALLBACK = 100
CALLBACKS_PER_BUFFER = 10
BUFFER_SIZE = SAMPLES_PER_CALLBACK * CALLBACKS_PER_BUFFER

# ---------------- BUFFER PROCESSING THREAD ----------------
class BufferProcessor(QObject):
    process_buffer = pyqtSignal(np.ndarray)

    def __init__(self, fs):
        super().__init__()
        self.fs = fs
        self.process_buffer.connect(self.save_data)

    def save_data(self, data):
        t = np.arange(data.shape[0]) / self.fs
        df = pd.DataFrame({"Time (s)": t, "Signal": data})
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        df.to_excel(f"data_{timestamp}.xlsx", index=False)
        print(f"[+] Guardado {len(data)} muestras")

# ---------------- DAQ TASK WITH CALLBACK ----------------
class DAQTask(Task):
    def __init__(self, plot_buffer, processor_signal):
        super().__init__()
        self.plot_buffer = plot_buffer
        self.processor_signal = processor_signal

        # Doble buffer
        self.buffer1 = np.empty(BUFFER_SIZE)
        self.buffer2 = np.empty(BUFFER_SIZE)
        self.current_buffer = self.buffer1
        self.index = 0

        self.CreateAIVoltageChan(CHANNEL, "", DAQmx_Val_Cfg_Default, -10.0, 10.0, DAQmx_Val_Volts, None)
        self.CfgSampClkTiming("", SAMPLE_RATE, DAQmx_Val_Rising, DAQmx_Val_ContSamps, SAMPLES_PER_CALLBACK)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, SAMPLES_PER_CALLBACK, 0)
        self.StartTask()

    def EveryNCallback(self):
        data = np.zeros(SAMPLES_PER_CALLBACK, dtype=np.float64)
        read = int32()
        self.ReadAnalogF64(SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, data, SAMPLES_PER_CALLBACK, byref(read), None)

        # Actualiza el plot buffer
        self.plot_buffer[:] = np.roll(self.plot_buffer, -SAMPLES_PER_CALLBACK)
        self.plot_buffer[-SAMPLES_PER_CALLBACK:] = data

        # Llena el buffer actual
        self.current_buffer[self.index:self.index+SAMPLES_PER_CALLBACK] = data
        self.index += SAMPLES_PER_CALLBACK

        # Si está lleno, intercambia buffers y lanza señal de guardado
        if self.index >= BUFFER_SIZE:
            full_buffer = self.current_buffer.copy()
            self.current_buffer = self.buffer1 if self.current_buffer is self.buffer2 else self.buffer2
            self.index = 0
            self.processor_signal.emit(full_buffer)

        return 0

# ---------------- INTERFAZ Y GRAFICA ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAQ Viewer")

        self.plot_buffer = np.zeros(1000)
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.curve = self.plot_widget.plot(self.plot_buffer, pen='y')

        # Procesador y hilo
        self.processor = BufferProcessor(SAMPLE_RATE)
        self.thread = QThread()
        self.processor.moveToThread(self.thread)
        self.thread.start()

        # DAQ Task
        self.task = DAQTask(self.plot_buffer, self.processor.process_buffer)

        # Temporizador para actualizar el plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)

    def update_plot(self):
        self.curve.setData(self.plot_buffer)

    def closeEvent(self, event):
        self.task.StopTask()
        self.task.ClearTask()
        self.thread.quit()
        self.thread.wait()
        event.accept()

# ---------------- MAIN ----------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
