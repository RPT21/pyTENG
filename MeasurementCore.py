import os
import sys
import time
import shutil
import numpy as np
import pandas as pd
import pyqtgraph as pg
from datetime import datetime
from ctypes import byref, c_int32
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter
from PyQt5.QtWidgets import (QApplication, QPushButton, QVBoxLayout, QWidget,
                             QLabel, QSpinBox, QHBoxLayout, QFileDialog, QInputDialog)
from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps, 
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer, 
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread, QTimer, pyqtSlot
from PyDAQmx import Task
from RaspberryInterface import RaspberryInterface
from MyMerger import Pickle_merge, CSV_merge
from pyqtgraph.parametertree import Parameter, ParameterTree

def set_group_readonly(group, readonly=True):
    group.setReadonly(readonly)
    for child in group.children():
        if child.hasChildren():
            set_group_readonly(child, readonly)
        else:
            child.setReadonly(readonly)

# ---------------- BUFFER PROCESSING THREAD ----------------
class BufferProcessor(QObject):
    process_buffer_signal = pyqtSignal(object)

    def __init__(self, fs, mainWindowReference, channel_config, parent=None):
        super().__init__(parent)
        self.fs = fs
        self.process_buffer_signal.connect(self.save_data)
        self.timestamp = 0
        self.local_path = None
        self.mainWindow = mainWindowReference
        self.isSaving = False
        self.channel_config = channel_config

    @pyqtSlot(object)
    def save_data(self, data):
        self.isSaving = True
        t = np.arange(data.shape[0]) / self.fs + self.timestamp
        self.timestamp = t[-1] + (t[1] - t[0])

        df = pd.DataFrame({"Time (s)": t})
        for channel_name in self.channel_config.keys():
            df[channel_name] = data[self.channel_config[channel_name][-1]]

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        df.to_pickle(f"{self.local_path}/DAQ_{timestamp}.pkl")
        self.isSaving = False
        print(f"[+] Saved {len(data)} samples")

# ---------------- DAQ TASK WITH CALLBACK ----------------
class DAQTask(Task):
    def __init__(self,
                 PLOT_BUFFER,
                 BUFFER_PROCESSOR_SIGNAL,
                 SIGNAL_SELECTOR,
                 BUFFER_SIZE,
                 CHANNELS,
                 SAMPLE_RATE,
                 SAMPLES_PER_CALLBACK,
                 AdquisitionProgramReference,
                 TRIGGER_SOURCE=None):

        super().__init__()
        
        self.SAMPLE_RATE = SAMPLE_RATE
        self.SAMPLES_PER_CALLBACK = SAMPLES_PER_CALLBACK
        self.BUFFER_SIZE = BUFFER_SIZE
        self.CHANNELS = CHANNELS
        self.number_channels = len(self.CHANNELS)

        self.plot_buffer = PLOT_BUFFER
        self.write_index = 0
        self.processor_signal = BUFFER_PROCESSOR_SIGNAL
        self.data_column_selector = SIGNAL_SELECTOR

        self.buffer1 = np.empty((self.BUFFER_SIZE, self.number_channels))
        self.buffer2 = np.empty((self.BUFFER_SIZE, self.number_channels))
        self.current_buffer = self.buffer1
        self.index = 0
        self.mainWindow = AdquisitionProgramReference

        for channel in list(self.CHANNELS.values()):
            self.CreateAIVoltageChan(channel[0]["port"], "", channel[0]["port_config"], -10.0, 10.0, DAQmx_Val_Volts, None)

        if TRIGGER_SOURCE:
            self.CfgDigEdgeStartTrig(TRIGGER_SOURCE, DAQmx_Val_Rising)

        self.CfgSampClkTiming("", self.SAMPLE_RATE, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.SAMPLES_PER_CALLBACK)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, self.SAMPLES_PER_CALLBACK, 0)
        self.StartTask()

    def EveryNCallback(self):
        try:
            data = np.empty((self.SAMPLES_PER_CALLBACK, self.number_channels), dtype=np.float64)
            read = c_int32()
            self.ReadAnalogF64(self.SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, data, data.size, byref(read), None)

            if self.mainWindow.actual_plotter is self:
                self.plot_buffer[self.write_index:self.write_index + self.SAMPLES_PER_CALLBACK] = data[:, self.data_column_selector.value()[-1]]
                self.write_index = (self.write_index + self.SAMPLES_PER_CALLBACK) % self.plot_buffer.size

            if self.mainWindow.moveLinMot[0]:
                self.current_buffer[self.index:self.index + self.SAMPLES_PER_CALLBACK, :] = data
                self.index += self.SAMPLES_PER_CALLBACK

                if self.index >= self.BUFFER_SIZE:
                    if not self.mainWindow.processor.isSaving:
                        full_buffer = self.current_buffer
                        self.current_buffer = self.buffer1 if self.current_buffer is self.buffer2 else self.buffer2
                        self.index = 0
                        self.processor_signal.emit(full_buffer)
                    else:
                        raise Exception("Fatal error thread race condition reached when saving into disk!")
        
        except Exception as e:
            print(f"DAQ error in callback: {e}")
            
        return 0

class DeviceCommunicator(QObject):

    start_adquisition_signal = pyqtSignal()
    stop_adquisition_signal = pyqtSignal()

    def __init__(self, mainWindowReference, parent=None,
                 RelayCodeTask = None,
                 LinMotTriggerTask = None,
                 LinMotTriggerLine = "Dev1/port0/line7",
                 PrepareRaspberryLine = "Dev1/port0/line6",
                 RaspberryStatus_0_Line = "Dev1/port1/line0",
                 RaspberryStatus_1_Line = "Dev1/port1/line1",
                 RelayCodeLines = "Dev1/port0/line0:5"):

        super().__init__(parent)

        self.mainWindow = mainWindowReference

        self.rb_hostname = "192.168.100.200"
        self.rb_port = 22
        self.rb_username = "TENG"
        self.rb_password = "raspberry"
        self.rb_remote_path = "/var/opt/codesys/PlcLogic/FTP_Folder"

        self.raspberry = RaspberryInterface(hostname=self.rb_hostname,
                                            port=self.rb_port,
                                            username=self.rb_username,
                                            password=self.rb_password)


        self.is_rb_connected = self.raspberry.connect()

        if not self.is_rb_connected:
            print("The program will work without using Raspberry Pi.")

        self.start_adquisition_signal.connect(self.start_adquisition)
        self.stop_adquisition_signal.connect(self.stop_adquisition)

        # DAQ Analog Task
        self.AnalogTasks = []
        for n, device in enumerate(self.mainWindow.CHANNELS):
            self.AnalogTasks.append(DAQTask(PLOT_BUFFER=self.mainWindow.plot_buffer,
                                BUFFER_PROCESSOR_SIGNAL=self.mainWindow.buffer_processors[n].process_buffer_signal,
                                SIGNAL_SELECTOR=None,
                                BUFFER_SIZE=self.mainWindow.BUFFER_SIZE,
                                CHANNELS=device["DAQ_CHANNELS"],
                                SAMPLE_RATE=self.mainWindow.SAMPLE_RATE,
                                SAMPLES_PER_CALLBACK=self.mainWindow.SAMPLES_PER_CALLBACK,
                                AdquisitionProgramReference=self.mainWindow,
                                TRIGGER_SOURCE=device["TRIGGER_SOURCE"]))

        # DAQ Digital task relay control line 0
        if not RelayCodeTask:
            self.DO_task_RelayCode = DigitalOutputTask_MultipleChannels(channels=RelayCodeLines)
            self.DO_task_RelayCode.StartTask()
        else:
            self.DO_task_RelayCode = RelayCodeTask

        # DAQ Digital Task LinMot
        if not LinMotTriggerTask:
            self.DO_task_LinMotTrigger = DigitalOutputTask(line=LinMotTriggerLine)
            self.DO_task_LinMotTrigger.StartTask()
        else:
            self.DO_task_LinMotTrigger = LinMotTriggerTask

        # DAQ Digital Task Prepare Raspberry
        self.DO_task_PrepareRaspberry = DigitalOutputTask(line=PrepareRaspberryLine)
        self.DO_task_PrepareRaspberry.StartTask()

        # Raspberry Read Task status bit 0
        self.DI_task_Raspberry_status_0 = DigitalInputTask(line=RaspberryStatus_0_Line)
        self.DI_task_Raspberry_status_0.StartTask()

        # Raspberry Read Task status bit 1
        self.DI_task_Raspberry_status_1 = DigitalInputTask(line=RaspberryStatus_1_Line)
        self.DI_task_Raspberry_status_1.StartTask()

    @pyqtSlot()
    def start_adquisition(self, iteration=0):

        if self.is_rb_connected:
            if iteration >= 5:
                print("\033[91mRaspberry Pi is not responding for 5 trials, stopping... \033[0m")
                return

            self.DO_task_PrepareRaspberry.set_line(1)

            loop_counter = 0
            while loop_counter < 10000:
                status_bit_0 = self.DI_task_Raspberry_status_0.read_line()
                status_bit_1 = self.DI_task_Raspberry_status_1.read_line()

                if status_bit_0 == 0 and status_bit_1 == 0:
                    loop_counter += 1
                elif status_bit_0 == 1 and status_bit_1 == 0:
                    break
                elif status_bit_0 == 0 and status_bit_1 == 1:
                    self.DO_task_PrepareRaspberry.set_line(0)
                    print("\033[91mError, impossible to prepare raspberry to record, check codesys invalid license error. Resetting Codesys, please wait... \033[0m")
                    self.raspberry.reset_codesys()
                    self.start_adquisition(iteration = iteration + 1)
                    return
                else:
                    self.DO_task_PrepareRaspberry.set_line(0)
                    print("\033[91mError, EtherCAT bus is not working, resetting Codesys, please wait...\033[0m")
                    self.raspberry.reset_codesys()
                    self.start_adquisition()
                    return

            if loop_counter >= 10000:
                self.DO_task_PrepareRaspberry.set_line(0)
                print("\033[91mError loop counter overflow, raspberry is not responding\033[0m")
                return

        for task in self.AnalogTasks:
            task.index = 0

        self.mainWindow.moveLinMot[0] = True

        if self.mainWindow.automatic_mode:
            self.DO_task_RelayCode.set_lines(self.mainWindow.RESISTANCE_DATA[self.mainWindow.iteration_index]["DAQ_CODE"])
        else:
            self.DO_task_RelayCode.set_lines(self.mainWindow.DAQ_CODE)

        self.DO_task_LinMotTrigger.set_line(1)
        self.mainWindow.start_adquisition_success_signal.emit()

    @pyqtSlot()
    def stop_adquisition(self):

        self.mainWindow.moveLinMot[0] = False

        self.DO_task_LinMotTrigger.set_line(0)
        self.DO_task_PrepareRaspberry.set_line(0)
        self.DO_task_RelayCode.set_lines([0,0,0,0,0,0])

        if self.task.index != 0:
            data = self.task.current_buffer[:self.task.index]

            # In this case this thread will do the saving
            self.mainWindow.processor.save_data(data)

            self.task.index = 0

        if self.is_rb_connected:
            loop_counter = 0
            while loop_counter < 10000:
                status_bit_0 = self.DI_task_Raspberry_status_0.read_line()
                status_bit_1 = self.DI_task_Raspberry_status_1.read_line()
                if status_bit_0 == 0 and status_bit_1 == 0:
                    break
                loop_counter += 1

            if loop_counter >= 10000:
                print("\033[91mError loop counter overflow, raspberry is not responding\033[0m")
                return

            self.raspberry.download_folder(self.rb_remote_path, local_path=self.mainWindow.processor.local_path)
            self.raspberry.remove_files_with_extension(self.rb_remote_path)

        if self.mainWindow.automatic_mode:

            # Wait motor return to the origin position and increase iteration_index
            self.mainWindow.update_button_signal.emit()
            self.mainWindow.iteration_index += 1

            if self.mainWindow.iteration_index <= self.mainWindow.iterations:
                print("Waiting LinMot to return to origin position")
                time.sleep(5)

        self.mainWindow.stop_adquisition_success_signal.emit()

# ---------------- INTERFACE AND PLOT  ----------------
class AdquisitionProgram(QWidget):
    
    trigger_adquisition_signal = pyqtSignal()
    start_adquisition_success_signal = pyqtSignal()
    stop_adquisition_success_signal = pyqtSignal()
    update_button_signal = pyqtSignal()
    
    def __init__(self,
                 CHANNELS,
                 automatic_mode=False,
                 RESISTANCE_DATA=None,
                 exp_dir=None, 
                 tribu_id=None,
                 rload_id=None,
                 DAQ_CODE=(0, 0, 0, 0, 0, 1),
                 measure_time=30, 
                 SAMPLE_RATE=10000,
                 SAMPLES_PER_CALLBACK=100,
                 CALLBACKS_PER_BUFFER=500,
                 TimeWindowLength=3,  # seconds
                 refresh_rate=10, # milliseconds
                 parent=None,
                 mainWindowButtons=None,
                 mainWindowParamGroups=None,
                 RelayCodeTask=None,
                 LinMotTriggerTask=None,
                 LinMotTriggerLine="Dev1/port0/line7",
                 PrepareRaspberryLine="Dev1/port0/line6",
                 RaspberryStatus_0_Line="Dev1/port1/line0",
                 RaspberryStatus_1_Line="Dev1/port1/line1",
                 RelayCodeLines="Dev1/port0/line0:5"):

        super().__init__(parent)
        self.setWindowTitle("DAQ Viewer")
        self.layout = QVBoxLayout(self)
        
        # Define the moveLinmot bool: 
        # We use a list because a bool is not referenced when passed as an argument
        self.moveLinMot = [False]
        self.LinMotTriggerTask = LinMotTriggerTask
        self.RelayCodeTask = RelayCodeTask
        
        # ---------------- CONFIG ----------------

        self.SAMPLE_RATE = SAMPLE_RATE
        self.SAMPLES_PER_CALLBACK = SAMPLES_PER_CALLBACK
        self.CALLBACKS_PER_BUFFER = CALLBACKS_PER_BUFFER
        self.BUFFER_SIZE = SAMPLES_PER_CALLBACK * CALLBACKS_PER_BUFFER

        self.TimeWindowLength = TimeWindowLength
        self.PLOT_BUFFER_SIZE = ((SAMPLE_RATE * TimeWindowLength) // SAMPLES_PER_CALLBACK) * SAMPLES_PER_CALLBACK
        self.refresh_rate = refresh_rate
        self.CHANNELS = CHANNELS
        
        self.automatic_mode = automatic_mode
        self.RESISTANCE_DATA = RESISTANCE_DATA
        self.iterations = 0
        self.iteration_index = 0
        self.DAQ_CODE = DAQ_CODE
        self.xClose = False
        self.mainWindowButtons = mainWindowButtons
        self.mainWindowParamGroups = mainWindowParamGroups
        self.actual_plotter = None

        # Check RESISTANCE_DATA when automatic_mode enabled
        if self.automatic_mode:
            if self.RESISTANCE_DATA is None:
                print("Automatic mode requires RESISTANCE_DATA to be set. Exiting.")
                self.xClose = True
                return

            self.iterations = len(self.RESISTANCE_DATA) - 1

        # Request experiments directory
        if exp_dir:
            self.exp_dir = exp_dir
        else:
            print("Please select the experiment directory.")
            self.exp_dir = QFileDialog.getExistingDirectory(self, "Select Experiment Directory")
            if not self.exp_dir or not os.path.isdir(self.exp_dir):
                print("No directory selected. Exiting.")
                self.xClose = True
                return
            self.exp_dir = os.path.normpath(self.exp_dir)

        # Request TribuId
        if tribu_id:
            self.tribu_id = tribu_id
        else:
            print("Please enter TribuId.")
            self.tribu_id, ok = QInputDialog.getText(self, "Input", "Enter TribuId:")
            if not ok or not self.tribu_id:
                print("No TribuId entered. Exiting.")
                self.xClose = True
                return

        self.plot_buffer = np.empty(self.PLOT_BUFFER_SIZE, dtype=float)
        self.plot_buffer.fill(np.nan)

        self.plot_widget = pg.PlotWidget()
        self.curve = self.plot_widget.plot(self.plot_buffer, pen='y')
        
        # Set rload_id if given:
        if rload_id and not self.automatic_mode:
            self.rload_id = rload_id
        else:
            self.rload_id = None

        # Adquisition control button:
        self.button = QPushButton("START LinMot")
        self.button.clicked.connect(self.trigger_adquisition)
        
        # Timer UI elements
        self.timer_label = QLabel("Duration (s):")
        self.timer_spinbox = QSpinBox()
        self.timer_spinbox.setRange(1, 86400)  # 1 sec to 24 hours
        self.timer_spinbox.setValue(measure_time)  # Default value
        self.countdown_display = QLabel("Remaining time: -")
        self.countdown_display.setAlignment(Qt.AlignRight)
        self.duration = QHBoxLayout()
        self.duration.addWidget(self.timer_label)
        self.duration.addWidget(self.timer_spinbox)
        
        # Timer setup
        self.measurement_timer = QTimer()
        self.measurement_timer.timeout.connect(self.update_countdown)
        self.remaining_seconds = 0
        self.should_save_data = False
        
        # Buffer processor and thread for each DAQ Task
        self.buffer_processors = []
        self.thread_savers = []
        for n in range(len(self.CHANNELS)):
            self.buffer_processors.append(BufferProcessor(self.SAMPLE_RATE, self, channel_config=None))
            self.thread_savers.append(QThread())

        for n in range(len(self.CHANNELS)):
            self.buffer_processors[n].moveToThread(self.thread_savers[n])
            self.thread_savers[n].start()

        # Raspberry Communicator + DAQ Analog Task (2 threads):
        self.dev_comunicator = DeviceCommunicator(mainWindowReference=self,
                                                  RelayCodeTask=RelayCodeTask,
                                                  LinMotTriggerTask=LinMotTriggerTask,
                                                  LinMotTriggerLine=LinMotTriggerLine,
                                                  PrepareRaspberryLine=PrepareRaspberryLine,
                                                  RaspberryStatus_0_Line=RaspberryStatus_0_Line,
                                                  RaspberryStatus_1_Line=RaspberryStatus_1_Line,
                                                  RelayCodeLines=RelayCodeLines)

        self.thread_communicator = QThread()
        self.dev_comunicator.moveToThread(self.thread_communicator)
        self.thread_communicator.start()
        
        # Plot update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(self.refresh_rate)

        # Signal management
        self.trigger_adquisition_signal.connect(self.trigger_adquisition)
        self.start_adquisition_success_signal.connect(self.start_adquisition_success)
        self.stop_adquisition_success_signal.connect(self.stop_adquisition_success)
        self.update_button_signal.connect(self.update_button)

        # Insert the DAQ Task reference in each channel and generate a dictionary with all channels
        total_channels = {}
        for n, device in enumerate(self.CHANNELS):
            for channel in device["DAQ_CHANNELS"].keys():
                device["DAQ_CHANNELS"][channel].insert(-1, self.dev_comunicator.AnalogTasks[n])
            total_channels = total_channels | device["DAQ_CHANNELS"]

        # Signal Selector
        self.signal_selector = Parameter.create(name='Signal', type='list', limits=total_channels)
        self.signal_selector.sigValueChanged.connect(self._update_DAQ_Plot_Buffer)

        # Now we can assign the signal selector to the DAQs:
        for task in self.dev_comunicator.AnalogTasks:
            task.data_column_selector = self.signal_selector

        # Assign plot buffer to a DAQ Task
        self.actual_plotter = self.dev_comunicator.AnalogTasks[0]

        # Set the layout
        self.tree = ParameterTree()
        self.tree.setParameters(self.signal_selector, showTop=True)
        self.layout.addWidget(self.tree)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.plot_widget)
        self.layout.addLayout(self.duration)
        self.layout.addWidget(self.countdown_display)

        if self.automatic_mode:
            print("Starting adquisition in automatic mode.")
            self.trigger_adquisition()

    def _update_DAQ_Plot_Buffer(self, param, value):

        # Stop plotting and reset buffer
        self.actual_plotter = None
        self.plot_buffer.fill(np.nan)

        # Reset the write_index pointer from the DAQ Task that is going to plot
        DAQ_Task_Reference = value[1]
        DAQ_Task_Reference.write_index = 0

        # Set the new plotter
        self.actual_plotter = DAQ_Task_Reference

    def update_countdown(self):
        if self.remaining_seconds > 0 and self.moveLinMot[0]:
            self.remaining_seconds -= 1
            self.countdown_display.setText(f"Remaining time: {self.remaining_seconds} s")
        else:
            self.measurement_timer.stop()
            self.countdown_display.setText("Remaining time: -")
            self.should_save_data = True
            self.trigger_adquisition()
    
    def update_plot(self):
        if self.actual_plotter:
            display_data = np.concatenate((
                self.plot_buffer[self.actual_plotter.write_index:],
                self.plot_buffer[:self.actual_plotter.write_index]
            ))
            self.curve.setData(display_data)

    @pyqtSlot()
    def start_adquisition_success(self):
        os.makedirs(os.path.join(self.exp_dir, "RawData"), exist_ok=True)
        self.processor.local_path = os.path.join(self.exp_dir, "RawData", self.exp_id)
        os.makedirs(self.processor.local_path, exist_ok=True)

        self.processor.timestamp = 0

        self.remaining_seconds = self.timer_spinbox.value()
        self.countdown_display.setText(f"Remaining time: {self.remaining_seconds} s")
        self.measurement_timer.start(1000)  # 1 sec
        self.should_save_data = False

        self.update_button()
        print("The adquisition has started successfully!")

    @pyqtSlot()
    def stop_adquisition_success(self):
        if self.should_save_data:
            
            self.daq_file = Pickle_merge(folder_path=self.processor.local_path, exp_id=self.exp_id)
            
            if self.dev_comunicator.is_rb_connected:
                self.motor_file = CSV_merge(folder_path=self.processor.local_path, exp_id=self.exp_id)
            else:
                self.motor_file = ""

            self.add_experiment_row()
            
            # Delete files after merge
            shutil.rmtree(self.processor.local_path)
            
            print("Experiment ended succesfully!")

        else:
            print("Experiment interrupted.")

        if self.automatic_mode:
            if self.iteration_index <= self.iterations:
                self.trigger_adquisition()
            else:
                print("All iterations finished, exiting.")
                self.close()
        else:
            self.update_button()

    def update_button(self):
        self.button.setText("STOP LinMot" if self.moveLinMot[0] else "START LinMot")

    @pyqtSlot()
    def trigger_adquisition(self):

        if self.sender() == self.button and self.automatic_mode:
            print("Automatic mode has been disabled, stopping adquisition.")
            self.automatic_mode = False

        if self.automatic_mode:
            print(f"Starting the iteration {self.iteration_index} of {self.iterations}")

        if self.moveLinMot[0]:
            # STOP ADQUISITION
            self.measurement_timer.stop()
            self.countdown_display.setText("Remaining time: -")
            self.dev_comunicator.stop_adquisition_signal.emit()
        else:
            # START ADQUISITION
            if not self.rload_id and not self.automatic_mode:
                print("\nPlease enter RloadId")
                self.rload_id, ok = QInputDialog.getText(self, "Input", "Enter RloadId:")
                if not ok or not self.rload_id:
                    print("No RloadId entered. Operation canceled.")
                    return
            else:
                self.rload_id = self.RESISTANCE_DATA[self.iteration_index]["RLOAD_ID"]

            self.date_now = datetime.now().strftime("%d%m%Y_%H%M%S")
            self.exp_id = f"{self.date_now}-{self.tribu_id}-{self.rload_id}"

            self.dev_comunicator.start_adquisition_signal.emit()

    def add_experiment_row(self):
        """Add a new row to ExpsDescription.xlsx with the experiment data if it doesn't already exist."""
        excel_path = os.path.join(self.exp_dir, "ExpsDescription.xlsx")
        
        if os.path.isfile(excel_path):
            wb = load_workbook(excel_path)
            ws = wb.active
            if not ws.tables:
                print(f"Could not save the experiment row because the Excel file {excel_path} has no tables.")
                return
        else:
            print(f"Could not save the experiment row because the Excel file {excel_path} was not found.")
            return

        table_name = list(ws.tables.keys())[0]
        table = ws.tables[table_name]
        start_cell, end_cell = table.ref.split(":")
        start_col = "".join(filter(str.isalpha, start_cell))
        start_row = int("".join(filter(str.isdigit, start_cell)))
        end_col = "".join(filter(str.isalpha, end_cell))
        end_row = int("".join(filter(str.isdigit, end_cell)))

        start_col_idx = column_index_from_string(start_col)
        end_col_idx = column_index_from_string(end_col)

        # Create the new row to be inserted
        new_row = [
            self.exp_id,
            self.tribu_id,
            self.date_now,
            self.daq_file,
            self.motor_file,
            "",
            self.rload_id
        ] + [""] * 23  # Empty columns to fill with blank spaces

        # Find the first empty row
        for row_idx in range(start_row, end_row + 1):
            row_cells = ws[row_idx]
            if all(cell.value in (None, "") for cell in row_cells[start_col_idx - 1:end_col_idx]):
                first_empty_row = row_idx
                break
        else:
            first_empty_row = end_row + 1

        # Insert the new row
        for i, value in enumerate(new_row, start=start_col_idx):
            ws.cell(row=first_empty_row, column=i, value=value)

        # Update the table range if needed
        new_end_row = max(end_row, first_empty_row)
        if new_end_row != end_row:
            new_ref = f"{start_col}{start_row}:{end_col}{new_end_row}"
            table.ref = new_ref

        # Adjust column widths (optional)
        for col_idx in range(start_col_idx, end_col_idx + 1):
            column_letter = get_column_letter(col_idx)
            max_length = 0
            for row in range(start_row, new_end_row + 1):  # Include new row
                cell = ws.cell(row=row, column=col_idx)
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column_letter].width = max_length + 2

        wb.save(excel_path)

    def closeEvent(self, event):

        print("\nClosing DAQ Viewer")

        if not self.xClose:
            # Cleanup DAQ tasks
            for task in self.dev_comunicator.AnalogTasks:
                task.StopTask()
                task.ClearTask()

            self.dev_comunicator.DO_task_LinMotTrigger.set_line(0)
            if not self.LinMotTriggerTask:
                self.dev_comunicator.DO_task_LinMotTrigger.StopTask()
                self.dev_comunicator.DO_task_LinMotTrigger.ClearTask()

            self.dev_comunicator.DO_task_RelayCode.set_lines([0,0,0,0,0,0])
            if not self.RelayCodeTask:
                self.dev_comunicator.DO_task_RelayCode.StopTask()
                self.dev_comunicator.DO_task_RelayCode.ClearTask()

            self.dev_comunicator.DO_task_PrepareRaspberry.set_line(0)
            self.dev_comunicator.DO_task_PrepareRaspberry.StopTask()
            self.dev_comunicator.DO_task_PrepareRaspberry.ClearTask()

            self.dev_comunicator.DI_task_Raspberry_status_0.StopTask()
            self.dev_comunicator.DI_task_Raspberry_status_0.ClearTask()

            self.dev_comunicator.DI_task_Raspberry_status_1.StopTask()
            self.dev_comunicator.DI_task_Raspberry_status_1.ClearTask()

            for thread in self.thread_savers:
                thread.quit()
                thread.wait()

            self.thread_communicator.quit()
            self.thread_communicator.wait()

            if self.moveLinMot[0] and os.path.isdir(self.processor.local_path):
                shutil.rmtree(self.processor.local_path)
                print(f"Temporary folder {self.processor.local_path} deleted on exit.")

        if self.mainWindowButtons:
            for button in self.mainWindowButtons:
                button.setEnabled(True)

        if self.mainWindowParamGroups:
            for param_group in self.mainWindowParamGroups:
                set_group_readonly(param_group, readonly=False)


        # Use the accept() method of the class QCloseEvent to close the QWidget (if not desired use the ignore() method)
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if self.xClose:
            # Close the QWidget as soon as it is created adding in the event loop a QTimer event
            QTimer.singleShot(0, self.close)

# ---------------- DIGITAL IO TASKS ----------------
class DigitalOutputTask(Task):
    def __init__(self, line):
        super().__init__()
        self.CreateDOChan(line, "", DAQmx_Val_ChanForAllLines)
        self.set_line(0)

    def set_line(self, value):
        data = np.array([value], dtype=np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, DAQmx_Val_GroupByChannel, data, None, None)

class DigitalOutputTask_MultipleChannels(Task):
    def __init__(self, channels):
        Task.__init__(self)
        self.CreateDOChan(channels, "", DAQmx_Val_ChanForAllLines)

    def set_lines(self, values):
        """values must be a list or an array of N values of type uint8 (0 or 1)"""
        data = np.array(values, dtype=np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, DAQmx_Val_GroupByChannel, data, None, None)

class DigitalInputTask(Task):
    def __init__(self, line):
        super().__init__()
        self.CreateDIChan(line, "", DAQmx_Val_ChanForAllLines)

    def read_line(self):
        data = np.zeros(1, dtype=np.uint8)
        read = c_int32()
        self.ReadDigitalLines(1, 10.0, 0, data, 1, read, None, None)
        return data[0]

# ---------------- MAIN ----------------
if __name__ == '__main__':

    # The order of definition is the order of saving into buffer so we need to put the order in the list
    CHANNELS = [
        {
            "NAME":"Dev1",

            "DAQ_CHANNELS":{
                "Voltage": [{"port":"Dev1/ai2", "port_config":DAQmx_Val_Diff}, 0],
                "Current": [{"port":"Dev1/ai3", "port_config":DAQmx_Val_RSE}, 1],
            },

            "TRIGGER_SOURCE":None
        },

        {
            "NAME":"Dev2",

            "DAQ_CHANNELS":{
                "LinMot_Enable": [{"port":"Dev2/ai0", "port_config":DAQmx_Val_RSE}, 0],
                "LinMot_Up_Down": [{"port":"Dev2/ai1", "port_config":DAQmx_Val_RSE}, 1]
            },

            "TRIGGER_SOURCE":"PFI0"
        }
    ]

    resistance_list = [{'VALUE': 5,
                      'ATENUATION': 1.0,
                      'DAQ_CODE': [0, 0, 0, 0, 0, 1],
                      'RLOAD_ID': 'Resistance 0'},
                     {'VALUE': 25,
                      'ATENUATION': 1.8,
                      'DAQ_CODE': [0, 0, 1, 0, 0, 1],
                      'RLOAD_ID': 'Resistance 4'},
                     {'VALUE': 35,
                      'ATENUATION': 2.2,
                      'DAQ_CODE': [0, 1, 1, 0, 0, 1],
                      'RLOAD_ID': 'Resistance 6'}]

    app = QApplication(sys.argv)
    window = AdquisitionProgram(CHANNELS, automatic_mode=False, RESISTANCE_DATA=resistance_list)
    window.show()
    sys.exit(app.exec_())


