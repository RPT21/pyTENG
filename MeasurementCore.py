import os
import sys
import shutil
import numpy as np
import pyqtgraph as pg
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter
from PyQt5.QtWidgets import (QApplication, QPushButton, QVBoxLayout, QWidget,
                             QLabel, QSpinBox, QHBoxLayout, QFileDialog, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, pyqtSlot
from MyMerger import Pickle_merge, CSV_merge
from pyqtgraph.parametertree import Parameter, ParameterTree
from ClassStructures.BufferProcessorClass import BufferProcessor
from ClassStructures.DeviceCommunicatorClass import DeviceCommunicator

from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def set_group_readonly(group, readonly=True):
    group.setReadonly(readonly)
    for child in group.children():
        if child.hasChildren():
            set_group_readonly(child, readonly)
        else:
            child.setReadonly(readonly)

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
        self.stop_for_error = False
        self.RESISTANCE_DATA = RESISTANCE_DATA
        self.iterations = 0
        self.iteration_index = 0
        self.DAQ_CODE = DAQ_CODE
        self.xClose = False
        self.mainWindowButtons = mainWindowButtons
        self.mainWindowParamGroups = mainWindowParamGroups
        self.actual_plotter = None
        self.local_path = [""]

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

        self.plot_buffer = np.empty(self.PLOT_BUFFER_SIZE, dtype=np.float64)
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
        self.device_names = []
        for n, device in enumerate(self.CHANNELS):
            self.buffer_processors.append(BufferProcessor(fs=self.SAMPLE_RATE,
                                                          mainWindowReference=self,
                                                          channel_config=device["DAQ_CHANNELS"],
                                                          task_name=device["NAME"]))
            self.thread_savers.append(QThread())
            self.device_names.append(device["NAME"])
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
                device["DAQ_CHANNELS"][channel].insert(-1, self.dev_comunicator.AdquisitionTasks[n])
            total_channels = total_channels | device["DAQ_CHANNELS"]

        # Signal Selector
        self.signal_selector = Parameter.create(name='Signal', type='list', limits=total_channels)
        self.signal_selector.sigValueChanged.connect(self._update_DAQ_Plot_Buffer)

        # Now we can assign the signal selector to the DAQs:
        for task in self.dev_comunicator.AdquisitionTasks:
            task.data_column_selector = self.signal_selector

        # Assign plot buffer to a DAQ Task
        self.actual_plotter = self.dev_comunicator.AdquisitionTasks[0]

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

    def reset_buffer(self):
        self.plot_buffer.fill(np.nan)

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
        self.local_path[0] = os.path.join(self.exp_dir, "RawData", self.exp_id)
        os.makedirs(self.local_path[0], exist_ok=True)

        for processor in self.buffer_processors:
            processor.timestamp = 0

        self.remaining_seconds = self.timer_spinbox.value()
        self.countdown_display.setText(f"Remaining time: {self.remaining_seconds} s")
        self.measurement_timer.start(1000)  # 1 sec
        self.should_save_data = False

        self.update_button()
        print("The adquisition has started successfully!")

    @pyqtSlot()
    def stop_adquisition_success(self):
        self.reset_buffer()
        if self.should_save_data:
            
            self.daq_file = Pickle_merge(folder_path=self.local_path[0], exp_id=self.exp_id, groupby=self.device_names)
            
            if self.dev_comunicator.is_rb_connected:
                self.motor_file = CSV_merge(folder_path=self.local_path[0], exp_id=self.exp_id)
            else:
                self.motor_file = ""

            self.add_experiment_row()
            
            # Delete files after merge
            shutil.rmtree(self.local_path[0])
            
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

        if self.stop_for_error:
            if self.sender() == self.button:
                self.stop_for_error = False
            else:
                # STOP ADQUISITION
                self.measurement_timer.stop()
                self.countdown_display.setText("Remaining time: -")
                self.dev_comunicator.stop_adquisition_signal.emit()
                print("Stopped adquisition due to an error.")
                return

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
            for task in self.dev_comunicator.AdquisitionTasks:
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

            if self.moveLinMot[0] and os.path.isdir(self.local_path[0]):
                shutil.rmtree(self.local_path[0])
                print(f"Temporary folder {self.local_path[0]} deleted on exit.")

        if self.mainWindowButtons:
            for button in self.mainWindowButtons.values():
                button.setEnabled(True)

        if self.mainWindowParamGroups:
            for param_group in self.mainWindowParamGroups.values():
                set_group_readonly(param_group, readonly=False)


        # Use the accept() method of the class QCloseEvent to close the QWidget (if not desired use the ignore() method)
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if self.xClose:
            # Close the QWidget as soon as it is created adding in the event loop a QTimer event
            QTimer.singleShot(0, self.close)

# ---------------- MAIN ----------------
if __name__ == '__main__':

    # The order of definition is the order of saving into buffer so we need to put the order in the list
    CHANNELS = [
        {
            "NAME":"Dev1",

            "DAQ_CHANNELS":{
                # "Voltage": [{"port":"Dev1/ai2", "port_config":DAQmx_Val_Diff}, 0],
                "Voltage": [{"port": "Dev1/ai3", "port_config": DAQmx_Val_Diff}, 0],
                # "Current": [{"port":"Dev1/ai3", "port_config":DAQmx_Val_RSE}, 1],
            },

            # "TRIGGER_SOURCE": "PFI0",
            "TRIGGER_SOURCE": None,

            "TYPE": "analog"
        },

        {
            "NAME":"Dev2",

            "DAQ_CHANNELS":{
                # "LinMot_Enable": [{"port":"Dev2/ai0", "port_config":DAQmx_Val_RSE}, 0],
                # "LinMot_Up_Down": [{"port":"Dev2/ai1", "port_config":DAQmx_Val_RSE}, 1]
                "LinMot_Enable": [{"port":"Dev2/port0/line0", "port_config":None}, 0],
                "LinMot_Up_Down": [{"port":"Dev2/port0/line1", "port_config":None}, 1]
            },

            # "TRIGGER_SOURCE": "PFI0",
            "TRIGGER_SOURCE": None,
            "TYPE": "digital"
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

    # To debug, use this
    debug = True
    if debug:
        exp_dir = r"C:\Users\rpieres\Desktop\Test"
        tribu_id = "C"
        rload_id = "Resistance 4"
    else:
        exp_dir = None
        tribu_id = None
        rload_id = None

    window = AdquisitionProgram(CHANNELS,
                                automatic_mode=False,
                                RESISTANCE_DATA=resistance_list,
                                measure_time=10,
                                exp_dir=exp_dir,
                                tribu_id=tribu_id,
                                rload_id=rload_id)
    window.show()
    sys.exit(app.exec_())


