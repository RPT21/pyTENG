import sys
import numpy as np
import pandas as pd
import time
import threading
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QFileDialog
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer, pyqtSlot
import pyqtgraph as pg
from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *
import tkinter as tk
import os
from RaspberryInterface import RaspberryInterface

# In this script we will try to work with 4 Threads:

# 1) Main Thread - Doing screen refresh and managing Window events like button clicks, etc...
# 2) AnalogRead Thread - Reading DAQ Analog Readings
# 3) DigitalIO and Raspberry Thread - Reading and Sending digital signals and doing the communication with Raspberry
# 4) Save Thread - Saving the data into the disk

# ### Buffers to test the speed of two diferent methods, numpy roll function or circular buffer.
# plot_array = np.zeros(1000)
# inip = 0
# buffer_display_array = np.zeros(1000)
# inibd = 0

# ---------------- CONFIG ----------------
CHANNEL = "Dev1/ai2"
SAMPLE_RATE = 10000
SAMPLES_PER_CALLBACK = 100  # Modulates the acquisition frequency
CALLBACKS_PER_BUFFER = 500 # Modulates when to save data
BUFFER_SIZE = SAMPLES_PER_CALLBACK * CALLBACKS_PER_BUFFER

TimeWindowLength = 3 # In seconds
PLOT_BUFFER_SIZE = ((SAMPLE_RATE * TimeWindowLength) // SAMPLES_PER_CALLBACK) * SAMPLES_PER_CALLBACK
refresh_rate = 10

# ---------------- BUFFER PROCESSING THREAD ----------------
class BufferProcessor(QObject):
    process_buffer = pyqtSignal(object)

    def __init__(self, fs, mainWindowReference, parent=None):
        super().__init__(parent)
        self.fs = fs
        self.process_buffer.connect(self.save_data)
        self.timestamp = 0
        self.local_path = None
        self.mainWindow = mainWindowReference

    @pyqtSlot(object)  # Decorador necessari perquè la funció no s'executi des de el thread que la crida sino des del thread on viu l'objecte
    def save_data(self, data):
        if self.mainWindow.moveLinMot:

            # ### Compare threads
            # print(f"\nSave called in thread: {QThread.currentThread()}")
            # print(f"Main thread: {QApplication.instance().thread()}")
            # print("Are they the same thread? ... ", QThread.currentThread() == QApplication.instance().thread(),"\n")

            t = np.arange(data.shape[0]) / self.fs
            t += self.timestamp
            self.timestamp = t[-1] + (t[1] - t[0])
            df = pd.DataFrame({"Time (s)": t, "Signal": data})
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # df.to_excel(os.path.join(self.local_path, f"DAQ_{timestamp}.xlsx"), index=False)  # No funciona per adquisicions ràpides
            df.to_pickle(os.path.join(self.local_path, f"DAQ_{timestamp}.pkl"))
            print(f"[+] Saved {len(data)} samples")


# ---------------- DAQ TASK WITH CALLBACK ----------------
class DAQTask(Task):
    def __init__(self, plot_buffer, processor_signal):
        super().__init__()

        # Plot buffer - Circular buffer
        self.plot_buffer = plot_buffer
        self.write_index = 0

        # Function to save the data
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

        ### Compare threads
        # print("Current Thread:", threading.current_thread())
        # print("Qt Thread:", QThread.currentThread())

        data = np.zeros(SAMPLES_PER_CALLBACK, dtype=np.float64)
        read = int32()
        self.ReadAnalogF64(SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, data, SAMPLES_PER_CALLBACK, byref(read), None)

        ### Actualitza el buffer del plot (circular buffer method)

        # inicio = time.perf_counter()

        # if self.write_index + SAMPLES_PER_CALLBACK < self.plot_buffer.size:
        #     self.plot_buffer[self.write_index:self.write_index + SAMPLES_PER_CALLBACK] = data
        #     self.write_index += SAMPLES_PER_CALLBACK
        # else:
        #     difference = PLOT_BUFFER_SIZE - (self.write_index + SAMPLES_PER_CALLBACK)
        #     self.plot_buffer[self.write_index:self.write_index + difference] = data[:difference]
        #     if difference > 0:
        #         self.plot_buffer[0:SAMPLES_PER_CALLBACK-difference] = data[SAMPLES_PER_CALLBACK-difference:]
        #         self.write_index = SAMPLES_PER_CALLBACK-difference
        #     else:
        #         self.write_index = 0

        # Making the buffer a multiple of SAMPLES_PER_CALLBACK
        self.plot_buffer[self.write_index:self.write_index + SAMPLES_PER_CALLBACK] = data
        self.write_index += SAMPLES_PER_CALLBACK

        if self.write_index == self.plot_buffer.size:
            self.write_index = 0

        # ### Actualitza el buffer del plot (numpy roll function method)
        # self.plot_buffer[:] = np.roll(self.plot_buffer, -SAMPLES_PER_CALLBACK)
        # self.plot_buffer[-SAMPLES_PER_CALLBACK:] = data

        # ### Testing code speed
        # fin = time.perf_counter()
        # global inibd
        # if inibd < 1000:
        #     plot_array[inibd] = fin - inicio
        #     inibd += 1
        # else:
        #     print(f"plot_array mean: {np.mean(plot_array):.9f}")

        ### Save data into the current buffer
        self.current_buffer[self.index:self.index + SAMPLES_PER_CALLBACK] = data
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

class DeviceCommunicator(QObject):

    start_acquisition_signal = pyqtSignal()
    stop_acquisition_signal = pyqtSignal()

    def __init__(self, mainWindowReference, parent=None):
        super().__init__(parent)

        self.mainWindow = mainWindowReference

        hostname = "192.168.100.200"
        port = 22
        username = "TENG"
        password = "raspberry"

        self.remote_path = "/var/opt/codesys/PlcLogic/FTP_Folder"

        self.raspberry = RaspberryInterface(hostname=hostname,
                                       port=port,
                                       username=username,
                                       password=password)

        self.thread_raspberry = QThread()
        self.raspberry.moveToThread(self.thread_raspberry)
        self.thread_raspberry.start()

        self.raspberry.execute.emit(lambda: self.raspberry.connect())

        self.start_acquisition_signal.connect(self.start_acquisition)
        self.stop_acquisition_signal.connect(self.stop_acquisition)

        # DAQ Analog Task
        self.task = DAQTask(self.mainWindow.plot_buffer, self.mainWindow.processor.process_buffer)

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

    @pyqtSlot()
    def start_acquisition(self):

        print("Starting acquisition")

        # Get file save location from user:
        print("Please provide a save location for incoming data.")
        self.mainWindow.processor.local_path = QFileDialog.getExistingDirectory(self.mainWindow, 
                                                                                "Select a Directory to save the data")
        if self.mainWindow.processor.local_path:
            self.mainWindow.processor.local_path = self.mainWindow.processor.local_path.replace("/", "\\")
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
            elif status_bit_0 == 1 and status_bit_1 == 0:  # OK and no error
                break
            elif status_bit_0 == 0 and status_bit_1 == 1:  # NOT OK and error
                self.DO_task_PrepareRaspberry.set_line(0)
                self.raspberry.execute.emit(lambda: self.raspberry.reset_codesys())
                print(
                    "\033[91mError, impossible to prepare raspberry to record, check codesys invalid license error. "
                    "Resetting Codesys, please wait... \033[0m")
                return
            else:
                self.DO_task_PrepareRaspberry.set_line(0)
                self.raspberry.execute.emit(lambda: self.raspberry.reset_codesys())
                print("\033[91mError, EtherCAT bus is not working, resetting Codesys, please wait...\033[0m")
                return

        if loop_counter >= 10000:
            self.DO_task_PrepareRaspberry.set_line(0)
            print("\033[91mError loop counter overflow, raspberry is not responding\033[0m")
            return

        self.task.index = 0  # Reset buffer index
        self.DO_task_LinMotTrigger.set_line(1)
        self.mainWindow.moveLinMot = True
        self.mainWindow.thread_signal_manager.emit(lambda: self.mainWindow.update_button())


    @pyqtSlot()
    def stop_acquisition(self):

        print("Stopping acquisition")

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
            print("\033[91mError loop counter overflow, raspberry is not responding\033[0m")
            return

        self.raspberry.execute.emit(lambda: self.raspberry.download_folder(self.remote_path, local_path=self.mainWindow.processor.local_path))
        self.raspberry.execute.emit(lambda: self.raspberry.remove_files_with_extension(self.remote_path))

        self.mainWindow.moveLinMot = False
        self.mainWindow.thread_signal_manager.emit(lambda: self.mainWindow.update_button())


# ---------------- INTERFACE AND PLOT  ----------------
class MainWindow(QWidget):
    
    thread_signal_manager = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAQ Viewer")
        self.layout = QVBoxLayout(self)
        self.moveLinMot = False

        self.plot_buffer = np.zeros(PLOT_BUFFER_SIZE, dtype=float)

        self.plot_widget = pg.PlotWidget()
        self.curve = self.plot_widget.plot(self.plot_buffer, pen='y')

        # Acquisition control button:
        self.button = QPushButton("START LinMot")
        self.button.clicked.connect(self.trigger_acquisition)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.plot_widget)

        # Buffer processor (save to disk) (1 thread)
        self.processor = BufferProcessor(SAMPLE_RATE, self)
        self.thread_saver = QThread()
        self.processor.moveToThread(self.thread_saver)
        self.thread_saver.start()

        # Raspberry Communicator + DAQ Analog Task (2 threads):
        self.dev_comunicator = DeviceCommunicator(mainWindowReference=self)
        self.thread_signal_manager.connect(self.run_function)
        self.thread_communicator = QThread()
        self.dev_comunicator.moveToThread(self.thread_communicator)
        self.thread_communicator.start()

        # QTimer to update plot view
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(refresh_rate)

    def update_plot(self):

        # ini_plot = time.perf_counter()

        ### Display DAQ signal (using circular buffer method)
        display_data = np.concatenate((
        self.plot_buffer[self.dev_comunicator.task.write_index:],
        self.plot_buffer[:self.dev_comunicator.task.write_index]
        ))
        self.curve.setData(display_data)


        # ### Display DAQ signal (using numpy roll function method)
        # self.curve.setData(self.plot_buffer)

        # end_plot = time.perf_counter()

        # ### Testing Display speed
        # global inip
        # if inip < 1000:
        #     buffer_display_array[inip] = end_plot - ini_plot
        #     inip += 1
        # else:
        #     print(f"Buffer display mean: {np.mean(buffer_display_array):.9f}")

    def closeEvent(self, event):

        self.dev_comunicator.task.StopTask()
        self.dev_comunicator.task.ClearTask()

        self.dev_comunicator.DO_task_LinMotTrigger.set_line(0)
        self.dev_comunicator.DO_task_LinMotTrigger.StopTask()
        self.dev_comunicator.DO_task_LinMotTrigger.ClearTask()

        self.dev_comunicator.DO_task_PrepareRaspberry.set_line(0)
        self.dev_comunicator.DO_task_PrepareRaspberry.StopTask()
        self.dev_comunicator.DO_task_PrepareRaspberry.ClearTask()

        self.dev_comunicator.DI_task_Raspberry_status_0.StopTask()
        self.dev_comunicator.DI_task_Raspberry_status_0.ClearTask()

        self.dev_comunicator.DI_task_Raspberry_status_1.StopTask()
        self.dev_comunicator.DI_task_Raspberry_status_1.ClearTask()

        self.thread_saver.quit()
        self.thread_saver.wait()

        self.thread_communicator.quit()
        self.thread_communicator.wait()

        event.accept()
        
    @pyqtSlot(object)
    def run_function(self, function):
        function()

    def update_button(self):
        self.button.setText("STOP LinMot" if self.moveLinMot else "START LinMot")

    def trigger_acquisition(self):
        if self.moveLinMot:
            print("moveLinMot is True")
            self.dev_comunicator.stop_acquisition_signal.emit()
        else:
            print("moveLinMot is False")
            self.dev_comunicator.start_acquisition_signal.emit()


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
