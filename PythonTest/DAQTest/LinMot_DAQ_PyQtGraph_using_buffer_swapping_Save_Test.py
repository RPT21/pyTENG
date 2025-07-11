import sys
import numpy as np
import pandas as pd
import time
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
import pyqtgraph as pg
from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *
import tkinter as tk
from tkinter import filedialog
import os
from RaspberryInterface import RaspberryInterface

# ---------------- CONFIG ----------------
CHANNEL = "Dev1/ai2"
SAMPLE_RATE = 100000
SAMPLES_PER_CALLBACK = 1000
CALLBACKS_PER_BUFFER = 1000
BUFFER_SIZE = SAMPLES_PER_CALLBACK * CALLBACKS_PER_BUFFER

TimeWindowLength = 10 # In seconds
PLOT_BUFFER_SIZE = int(SAMPLE_RATE * TimeWindowLength)

moveLinMot = False

# ---------------- BUFFER PROCESSING THREAD ----------------
class BufferProcessor(QObject):
    process_buffer = pyqtSignal(np.ndarray)

    def __init__(self, fs):
        super().__init__()
        self.fs = fs
        self.process_buffer.connect(self.save_data)
        self.timestamp = 0
        self.local_path = None

    def save_data(self, data):
        if moveLinMot:
            t = np.arange(data.shape[0]) / self.fs
            t += self.timestamp
            self.timestamp = t[-1] + (t[1] - t[0])
            df = pd.DataFrame({"Time (s)": t, "Signal": data})
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            df.to_excel(os.path.join(self.local_path, f"DAQ_{timestamp}.xlsx"), index=False)
            print(f"[+] Saved {len(data)} samples")

# ---------------- DAQ TASK WITH CALLBACK ----------------
class DAQTask(Task):
    def __init__(self, plot_buffer, processor_signal):
        super().__init__()
        self.plot_buffer = plot_buffer
        self.processor_signal = processor_signal

        # Buffer swapping - double buffer
        self.buffer1 = np.empty(BUFFER_SIZE)
        self.buffer2 = np.empty(BUFFER_SIZE)
        self.current_buffer = self.buffer1
        self.index = 0

        self.CreateAIVoltageChan(CHANNEL, "", DAQmx_Val_Diff, -10.0, 10.0, DAQmx_Val_Volts, None)
        self.CfgSampClkTiming("", SAMPLE_RATE, DAQmx_Val_Rising, DAQmx_Val_ContSamps, SAMPLES_PER_CALLBACK)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, SAMPLES_PER_CALLBACK, 0)
        self.StartTask()

    def EveryNCallback(self):
        data = np.zeros(SAMPLES_PER_CALLBACK, dtype=np.float64)
        read = int32()
        self.ReadAnalogF64(SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, data, SAMPLES_PER_CALLBACK, byref(read), None)

        # Actualitza el buffer del plot
        self.plot_buffer[:] = np.roll(self.plot_buffer, -SAMPLES_PER_CALLBACK)
        self.plot_buffer[-SAMPLES_PER_CALLBACK:] = data

        # Omple el buffer actual
        self.current_buffer[self.index:self.index+SAMPLES_PER_CALLBACK] = data
        self.index += SAMPLES_PER_CALLBACK

        # Si el buffer que la DAQ està utilitzant s'omple, envia un emit perquè es guardi en el disc i intercanvia
        # els buffers, ara la DAQ escriu en l'altre buffer mentre el que està ple es guarda en el disc.
        if self.index >= BUFFER_SIZE:

            # En principi el thread de guardar en disc és més ràpid, i tarda menys temps a guardar tot el buffer que el
            # que tarda l'altre thread a omplir l'altre buffer i intercanviar-lo. Si aquesta condició es compleix sempre,
            # no hi pot haver condició de carrera i aquest mètode hauria de funcionar. Llavors, no fa falta fer un copy().
            # full_buffer = self.current_buffer.copy()

            full_buffer = self.current_buffer
            self.current_buffer = self.buffer1 if self.current_buffer is self.buffer2 else self.buffer2
            self.index = 0
            self.processor_signal.emit(full_buffer)  # Li passem la referència del buffer amb les dades

        return 0

# ---------------- INTERFACE AND PLOT  ----------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAQ Viewer")
        self.layout = QVBoxLayout(self)

        self.plot_buffer = np.zeros(PLOT_BUFFER_SIZE)
        self.plot_widget = pg.PlotWidget()
        self.curve = self.plot_widget.plot(self.plot_buffer, pen='y')

        hostname = "192.168.100.200"
        port = 22
        username = "TENG"
        password = "raspberry"

        self.remote_path = "/var/opt/codesys/PlcLogic/FTP_Folder"

        self.raspberry = RaspberryInterface(hostname=hostname,
                                       port=port,
                                       username=username,
                                       password=password)

        self.raspberry.connect()

        # Adquisition control button:
        self.button = QPushButton("START LinMot")
        self.button.clicked.connect(self.toggle_linmot)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.plot_widget)

        # Buffer processor (save to disk) thread
        self.processor = BufferProcessor(SAMPLE_RATE)
        self.thread = QThread()
        self.processor.moveToThread(self.thread)
        self.thread.start()

        # DAQ Analog Task
        self.task = DAQTask(self.plot_buffer, self.processor.process_buffer)

        # DAQ Digital Task LinMot
        self.DO_task_LinMotTrigger = DigitalOutputTask(line="Dev1/port0/line7")
        self.DO_task_LinMotTrigger.StartTask()

        # DAQ Digital Task Prepare Raspberry
        self.DO_task_PrepareRaspberry = DigitalOutputTask(line="Dev1/port0/line6")
        self.DO_task_PrepareRaspberry.StartTask()

        # Raspberry Read Task status bit 0
        self.DI_task_Raspberry_status_0 = DigitalInputTask(line="Dev1/port1/line0")
        self.DI_task_Raspberry_status_0.StartTask()

        # Raspberry Read Task status bit 1
        self.DI_task_Raspberry_status_1 = DigitalInputTask(line="Dev1/port1/line1")
        self.DI_task_Raspberry_status_1.StartTask()

        # QTimer to update plot view
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)

    def update_plot(self):
        self.curve.setData(self.plot_buffer)

    def closeEvent(self, event):
        self.task.StopTask()
        self.task.ClearTask()

        self.DO_task_LinMotTrigger.set_line(0)
        self.DO_task_LinMotTrigger.StopTask()
        self.DO_task_LinMotTrigger.ClearTask()

        self.DO_task_PrepareRaspberry.set_line(0)
        self.DO_task_PrepareRaspberry.StopTask()
        self.DO_task_PrepareRaspberry.ClearTask()

        self.DI_task_Raspberry_status_0.StopTask()
        self.DI_task_Raspberry_status_0.ClearTask()

        self.DI_task_Raspberry_status_1.StopTask()
        self.DI_task_Raspberry_status_1.ClearTask()

        self.thread.quit()
        self.thread.wait()
        event.accept()

    def toggle_linmot(self):
        global moveLinMot
        if moveLinMot:
            # Stop LinMot and save data
            self.DO_task_LinMotTrigger.set_line(0)
            self.DO_task_PrepareRaspberry.set_line(0)
            if self.task.index != 0:
                data = self.task.current_buffer[0:self.task.index]
                self.task.processor_signal.emit(data)
                self.task.index = 0

            loop_counter = 0

            while loop_counter < 10000:
                status_bit_0 = self.DI_task_Raspberry_status_0.read_line()
                status_bit_1 = self.DI_task_Raspberry_status_1.read_line()

                if status_bit_0 == 0 and status_bit_1 == 0:
                    break
                else:
                    loop_counter += 1

            if loop_counter >= 10000:
                raise Exception("Error loop counter overflow")

            self.raspberry.download_folder(self.remote_path, local_path=self.processor.local_path)
            self.raspberry.remove_files_with_extension(self.remote_path)
        else:
            # Get file save location from user:
            print("Please provide a save location for incoming data.")
            root = tk.Tk()
            root.withdraw()  # Amaga la finestra princial de tkinter
            root.lift()  # Posa la finestra emergent en primer pla
            root.attributes('-topmost', True)  # La finestra sempre al davant

            self.processor.local_path = filedialog.askdirectory()

            if self.processor.local_path:
                self.processor.local_path = self.processor.local_path.replace("/", "\\")
            else:
                print("Canceled")
                return

            # Start LinMot and reset buffer index counter
            self.DO_task_PrepareRaspberry.set_line(1)

            loop_counter = 0

            while loop_counter < 10000:
                status_bit_0 = self.DI_task_Raspberry_status_0.read_line()
                status_bit_1 = self.DI_task_Raspberry_status_1.read_line()

                if status_bit_0 == 0 and status_bit_1 == 0:
                    loop_counter += 1
                elif status_bit_0 == 1 and status_bit_1 == 0: # OK and no error
                    break
                elif status_bit_0 == 0 and status_bit_1 == 1: # NOT OK and error
                    self.DO_task_PrepareRaspberry.set_line(0)
                    raise Exception("Error, impossible to prepare raspberry to record")
                else:
                    self.DO_task_PrepareRaspberry.set_line(0)
                    self.raspberry.reset_codesys()
                    raise Exception("Error, EtherCAT bus is not working, it has been reset, try again")

            if loop_counter >= 10000:
                self.DO_task_PrepareRaspberry.set_line(0)
                raise Exception("Error loop counter overflow")

            self.task.index = 0  # Reset buffer index
            self.DO_task_LinMotTrigger.set_line(1)

        moveLinMot = not moveLinMot
        self.button.setText("STOP LinMot" if moveLinMot else "START LinMot")


class DigitalOutputTask(Task):
    def __init__(self, line="Dev1/port0/line7"):
        Task.__init__(self)
        self.CreateDOChan(line, "", DAQmx_Val_ChanForAllLines)
        self.set_line(0)

    def set_line(self, value):
        """value = 0 (OFF) o 1 (ON)"""
        data = np.array([value], dtype=np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, DAQmx_Val_GroupByChannel, data, None, None)

class DigitalInputTask(Task):
    def __init__(self, line="Dev1/port1/line0"):
        Task.__init__(self)
        self.CreateDIChan(line, "", DAQmx_Val_ChanForAllLines)

    def read_line(self):
        data = np.zeros((1,), dtype=np.uint8)
        read = c_int32()
        self.ReadDigitalLines(1, 10.0, 0, data, 1, read, None, None)
        return data[0]


# ---------------- MAIN ----------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
