import os
import sys
import shutil
import numpy as np
import pyqtgraph as pg
from datetime import datetime
from openpyxl import load_workbook
import ezodf
from copy import copy
from openpyxl.utils import column_index_from_string
from PyQt5.QtWidgets import (QApplication, QPushButton, QVBoxLayout, QWidget,
                             QLabel, QSpinBox, QHBoxLayout, QFileDialog, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, pyqtSlot
from MyMerger import CSV_merge
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
class AcquisitionProgram(QWidget):

    trigger_acquisition_signal = pyqtSignal()
    start_acquisition_return_signal = pyqtSignal()
    stop_acquisition_return_signal = pyqtSignal()
    update_button_signal = pyqtSignal()
    
    def __init__(self,
                 DAQ_TASKS,
                 automatic_mode=False,
                 RESISTANCE_DATA=None,
                 exp_dir=None,
                 tribu_id=None,
                 rload_id=None,
                 DAQ_CODE=(0, 0, 0, 0, 0, 1),
                 measure_time=30,
                 DAQ_USB_TRANSFER_FREQUENCY=50,  # USB transfers per second (Hz)
                 BUFFER_SAVING_TIME_INTERVAL=2.5,  # Save buffer to disk every X seconds
                 TimeWindowLength=3,  # Time window length for the plot (seconds)
                 ScreenRefreshFrequency=60,  # Screen Refresh Rate (Hz)
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
        self.xRecording = [False]
        self.LinMotTriggerTask = LinMotTriggerTask
        self.RelayCodeTask = RelayCodeTask
        
        # ---------------- CONFIG ----------------

        # DAQ acquisition parameters
        self.DAQ_USB_TRANSFER_FREQUENCY = DAQ_USB_TRANSFER_FREQUENCY
        self.BUFFER_SAVING_TIME_INTERVAL = BUFFER_SAVING_TIME_INTERVAL
        self.ACQUISITION_PARAMS = {}

        # Plot parameters
        self.TimeWindowLength = TimeWindowLength
        self.refresh_rate = int((1 / ScreenRefreshFrequency * 1000))  # Convert to milliseconds for QTimer

        # Calculate buffer sizes for each DAQ Task
        for task in DAQ_TASKS:

            if task["SAMPLE_RATE"] % DAQ_USB_TRANSFER_FREQUENCY != 0:
                print(f"Warning: The sample rate of task {task['NAME']} is not an integer multiple of the DAQ USB Transfer Frequency.")
                print(f"Finding the closest DAQ USB transfer frequency that is a divisor of {task["SAMPLE_RATE"]} Hz.")

                divisors = set()
                for i in range(1, int(np.sqrt(task["SAMPLE_RATE"])) + 1):
                    if task["SAMPLE_RATE"] % i == 0:
                        divisors.add(i)
                        divisors.add(task["SAMPLE_RATE"] // i)

                # Keep only divisors greater or equal than 10
                valid_divisors = [d for d in divisors if d >= 10]

                # Find the closest to target
                CORRECTED_USB_FREQUENCY = min(valid_divisors, key=lambda x: abs(x - DAQ_USB_TRANSFER_FREQUENCY))
                print(f"The new USB transfer frequency for task {task['NAME']} is: ", CORRECTED_USB_FREQUENCY, " Hz.")
            else:
                CORRECTED_USB_FREQUENCY = DAQ_USB_TRANSFER_FREQUENCY

            # Calculate buffer parameters based on task sample rate
            samples_per_callback = int(task["SAMPLE_RATE"] / CORRECTED_USB_FREQUENCY)
            callbacks_per_buffer = int(BUFFER_SAVING_TIME_INTERVAL * CORRECTED_USB_FREQUENCY)
            plot_buffer_size = ((task["SAMPLE_RATE"] * TimeWindowLength) // samples_per_callback) * samples_per_callback

            self.ACQUISITION_PARAMS[task["NAME"]] = {
                'SAMPLES_PER_CALLBACK': samples_per_callback,
                'BUFFER_SIZE': samples_per_callback * callbacks_per_buffer,
                'PLOT_BUFFER_SIZE': plot_buffer_size
            }

        self.DAQ_TASKS = DAQ_TASKS
        
        self.automatic_mode = automatic_mode
        self.error_flag = False
        self.RESISTANCE_DATA = RESISTANCE_DATA
        self.iterations = 0
        self.iteration_index = 0
        self.DAQ_CODE = DAQ_CODE
        self.xClose = False
        self.mainWindowButtons = mainWindowButtons
        self.mainWindowParamGroups = mainWindowParamGroups
        self.actual_plotter = None
        self.index_pointer = None
        self.local_path = [""]

        # The order of definition is the order of saving into buffer, so we introduce an index to know the position:
        for task in DAQ_TASKS:
            for idx, (name, config) in enumerate(task["DAQ_CHANNELS"].items()):
                task["DAQ_CHANNELS"][name] = [config, idx]

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

        # Set rload_id if given:
        if rload_id and not self.automatic_mode:
            self.rload_id = rload_id
        else:
            self.rload_id = None

        # Define the plot widget
        self.plot_widget = pg.PlotWidget()
        self.curve = self.plot_widget.plot([], pen='y')
        self.display_data = np.array([], dtype=np.float64)

        # Acquisition control button:
        self.button = QPushButton("START LinMot")
        self.button.clicked.connect(self.trigger_acquisition)
        
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
        self.task_names = []
        for n, task in enumerate(self.DAQ_TASKS):
            self.buffer_processors.append(BufferProcessor(fs=task["SAMPLE_RATE"],
                                                          mainWindowReference=self,
                                                          channel_config=task["DAQ_CHANNELS"],
                                                          task_name=task["NAME"],
                                                          task_type=task["TYPE"]))
            self.thread_savers.append(QThread())
            self.task_names.append(task["NAME"])
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
        self.trigger_acquisition_signal.connect(self.trigger_acquisition)
        self.start_acquisition_return_signal.connect(self.start_acquisition_return)
        self.stop_acquisition_return_signal.connect(self.stop_acquisition_return)
        self.update_button_signal.connect(self.update_button)

        # Insert the DAQ Task reference in each channel and generate a dictionary with all channels
        total_tasks = {}
        for n, task in enumerate(self.DAQ_TASKS):
            for channel in task["DAQ_CHANNELS"].keys():
                task["DAQ_CHANNELS"][channel].insert(-1, self.dev_comunicator.AcquisitionTasks[n])
            total_tasks = total_tasks | task["DAQ_CHANNELS"]

        # Signal Selector
        self.signal_selector = Parameter.create(name='Signal', type='list', limits=total_tasks)
        self.signal_selector.sigValueChanged.connect(self._update_DAQ_Plot_Buffer)

        # Now we can assign the signal selector to the DAQs:
        for task in self.dev_comunicator.AcquisitionTasks:
            task.data_column_selector = self.signal_selector

        # Set the layout
        self.tree = ParameterTree()
        self.tree.setParameters(self.signal_selector, showTop=True)
        self.layout.addWidget(self.tree)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.plot_widget)
        self.layout.addLayout(self.duration)
        self.layout.addWidget(self.countdown_display)

        if self.automatic_mode:
            print("Starting acquisition in automatic mode.")
            self.trigger_acquisition()

    def _update_DAQ_Plot_Buffer(self, param, value):
        # Obtain the DAQ Task Reference
        DAQ_Task_Reference = value[1]

        # Disconnect the plotter from the screen
        self.actual_plotter = None

        # Reshape the display_data buffer
        if self.display_data.size != DAQ_Task_Reference.PLOT_BUFFER_SIZE:
            self.display_data = np.empty(DAQ_Task_Reference.PLOT_BUFFER_SIZE, dtype=np.float64)

        # Calculate the array index corresponding to the selected signal
        self.index_pointer = self.signal_selector.value()[-1]

        # Select the actual plotter
        self.actual_plotter = DAQ_Task_Reference

    def flush_screen(self):
        self.actual_plotter = None
        self.curve.setData([])

    def update_countdown(self):

        if self.dev_comunicator.is_rb_connected:
            # It takes aprox 10e-5 seconds to read the status bits
            status_bit_0 = self.dev_comunicator.DI_task_Raspberry_status_0.read_line()
            status_bit_1 = self.dev_comunicator.DI_task_Raspberry_status_1.read_line()

            if not (status_bit_0 == 1 and status_bit_1 == 0):
                if not self.error_flag:
                    # An error has occurred during the data acquisition
                    print(f"\033[91mError, during the acquisition, the Raspberry sent an error code:\033[0m", f"{status_bit_0}{status_bit_1}")
                    self.error_flag = True
                    self.trigger_acquisition()
            
        if not self.error_flag:
            if self.remaining_seconds > 0 and self.moveLinMot[0]:
                self.remaining_seconds -= 1
                self.countdown_display.setText(f"Remaining time: {self.remaining_seconds} s")
            else:
                self.measurement_timer.stop()
                self.countdown_display.setText("Remaining time: -")
                self.should_save_data = True
                self.trigger_acquisition()
    
    def update_plot(self):
        if self.actual_plotter is None:
            return
        if self.display_data.size == 0:
            return

        plot_buffer = self.actual_plotter.plot_buffer
        plot_buffer_size = self.actual_plotter.PLOT_BUFFER_SIZE
        write_index = self.actual_plotter.write_index

        tail_size = plot_buffer_size - write_index
        self.display_data[:tail_size] = plot_buffer[write_index:, self.index_pointer]
        self.display_data[tail_size:] = plot_buffer[:write_index, self.index_pointer]

        self.curve.setData(self.display_data)


    @pyqtSlot()
    def start_acquisition_return(self):

        if not self.error_flag:
            self.remaining_seconds = self.timer_spinbox.value()
            self.countdown_display.setText(f"Remaining time: {self.remaining_seconds} s")
            self.measurement_timer.start(1000)  # 1 sec
            self.should_save_data = False

            # Assign the plotter to the selected signal
            self.actual_plotter = self.signal_selector.value()[-2]

            self.update_button()
            print("The acquisition has started successfully!")

        else:
            # Close the opened files
            for processor in self.buffer_processors:
                processor.close_file()

            # Delete the folder created
            shutil.rmtree(self.local_path[0])

    @pyqtSlot()
    def stop_acquisition_return(self):

        # Clean the screen
        self.flush_screen()

        # Close the opened files
        for processor in self.buffer_processors:
            processor.close_file()

        if not self.error_flag:
            if self.should_save_data:

                # Convert the DAQ binary files to pandas dataframes
                for processor in self.buffer_processors:
                    processor.Binary_to_Pickle()

                # Merge the LinMot CSV files
                if self.dev_comunicator.is_rb_connected:
                    self.motor_file = CSV_merge(folder_path=self.local_path[0], exp_id=self.exp_id)
                else:
                    self.motor_file = ""

                self.add_experiment_row()

                print("Experiment ended succesfully!")
            else:
                print("Experiment interrupted.")

            if self.automatic_mode:
                if self.iteration_index <= self.iterations:
                    self.trigger_acquisition()
                else:
                    print("All iterations finished, exiting.")
                    self.close()
            else:
                self.update_button()
        else:
            self.update_button()
            print("Experiment interrupted due to an error.")

        # Delete temporal files if no error, if error, delete all
        if not self.error_flag:
            for processor in self.buffer_processors:
                processor.remove_file()
        else:
            # Delete all files
            shutil.rmtree(self.local_path[0])

    def update_button(self):
        self.button.setText("STOP LinMot" if self.moveLinMot[0] else "START LinMot")

    @pyqtSlot()
    def trigger_acquisition(self):

        if self.sender() == self.button and self.automatic_mode:
            print("Automatic mode has been disabled, stopping acquisition.")
            self.automatic_mode = False

        if self.error_flag:
            if self.sender() == self.button:
                self.error_flag = False
            else:
                # STOP ADQUISITION
                self.measurement_timer.stop()
                self.countdown_display.setText("Remaining time: -")
                self.dev_comunicator.stop_acquisition_signal.emit()
                print("Stopped acquisition due to an error.")
                return

        if self.automatic_mode:
            print(f"Starting the iteration {self.iteration_index} of {self.iterations}")

        if self.moveLinMot[0]:
            # STOP ADQUISITION
            self.measurement_timer.stop()
            self.countdown_display.setText("Remaining time: -")
            self.dev_comunicator.stop_acquisition_signal.emit()
        else:
            # START ADQUISITION
            if self.automatic_mode:
                self.rload_id = self.RESISTANCE_DATA[self.iteration_index]["RLOAD_ID"]
            elif not self.rload_id:
                print("\nPlease enter RloadId")
                self.rload_id, ok = QInputDialog.getText(self, "Input", "Enter RloadId:")
                if not ok or not self.rload_id:
                    print("No RloadId entered. Operation canceled.")
                    return

            self.date_now = datetime.now().strftime("%d%m%Y_%H%M%S")
            self.exp_id = f"{self.date_now}-{self.tribu_id}-{self.rload_id}"

            # Create necessary folders and define the saving path
            os.makedirs(os.path.join(self.exp_dir, "RawData"), exist_ok=True)
            self.local_path[0] = os.path.join(self.exp_dir, "RawData", self.exp_id)
            os.makedirs(self.local_path[0], exist_ok=True)

            # Open the files to save the data
            for processor in self.buffer_processors:
                processor.open_file()

            self.dev_comunicator.start_acquisition_signal.emit()

    def add_experiment_row(self, base_filename="Experiments"):
        """
        Search for Experiments file (.xlsx or .ods) in the directory
        and append a new experiment row depending on its format.
        """
        folder_path = os.path.dirname(self.local_path[0])
        xlsx_path = os.path.join(folder_path, f"{base_filename}.xlsx")
        ods_path = os.path.join(folder_path, f"{base_filename}.ods")

        if os.path.isfile(xlsx_path):
            file_path = xlsx_path
            file_type = "excel"
        elif os.path.isfile(ods_path):
            file_path = ods_path
            file_type = "openoffice"
        else:
            print(
                f"Could not save the experiment row. Neither {base_filename}.xlsx nor {base_filename}.ods were found.")
            return

        # Read the string and tell Python what each number represents
        # %d = day, %m = month, %Y = year (4 digits), %H = hour, %M = minute, %S = second
        date_object = datetime.strptime(self.date_now, "%d%m%Y_%H%M%S")

        # Extract from the date the day, month, year
        date_time = date_object.date()

        # Try to convert the rload_id to integer:
        try:
            rload_id = int(self.rload_id)
        except:
            rload_id = self.rload_id

        # 1. Calculamos el camino relativo desde el Excel hasta la carpeta destino
        ruta_relativa = os.path.relpath(self.local_path[0], start=self.exp_dir)

        # 2. TRUCO VITAL: Los hipervínculos en Excel y ODS requieren barras diagonales (/)
        # incluso en Windows. Si no haces esto, el enlace fallará al hacer clic.
        enlace_seguro = ruta_relativa.replace('\\', '/')

        # 2. Prepare the common new row data
        new_row = [
                      f"{self.tribu_id}-{self.rload_id}",
                      self.tribu_id,
                      date_time,
                      self.exp_id,
                      "none",
                      rload_id
                  ] + [""] * 23

        # 3. Process according to file type
        if file_type == "excel":
            self._add_to_excel(file_path, new_row)
        elif file_type == "openoffice":
            self._add_to_ods(file_path, new_row)

    def _add_to_excel(self, file_path, new_row):
        """Helper method to handle .xlsx files using openpyxl."""
        wb = load_workbook(file_path)
        ws = wb.active

        if not ws.tables:
            print(f"Could not save the experiment row because the Excel file {file_path} has no tables.")
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
            new_cell = ws.cell(row=first_empty_row, column=i, value=value)

            # Copy the format of the upper row (if this is not the first row)
            if first_empty_row > 1:
                old_cell = ws.cell(row=first_empty_row - 1, column=i)

                new_cell.font = copy(old_cell.font)
                new_cell.border = copy(old_cell.border)
                new_cell.fill = copy(old_cell.fill)
                new_cell.number_format = copy(old_cell.number_format)
                new_cell.alignment = copy(old_cell.alignment)

        # Update the table range
        new_end_row = max(end_row, first_empty_row)
        if new_end_row != end_row:
            table.ref = f"{start_col}{start_row}:{end_col}{new_end_row}"

        wb.save(file_path)

    def _add_to_ods(self, file_path, new_row):
        """Helper method to handle .ods files using ezodf."""
        doc = ezodf.opendoc(file_path)
        sheet = doc.sheets[0]

        # Find the first empty row
        first_empty_row = None
        for row_idx, row in enumerate(sheet.rows()):
            if all(cell.value is None or str(cell.value).strip() == "" for cell in row):
                first_empty_row = row_idx
                break

        # If no empty row is found, append a new structural row at the end
        if first_empty_row is None:
            first_empty_row = sheet.nrows()
            sheet.append_rows(1)

        # Insert the new data cell by cell and copy style
        for col_idx, value in enumerate(new_row):
            # Add columns structurally if needed
            if col_idx >= sheet.ncols():
                sheet.append_columns(1)

            # Select objective cell
            new_cell = sheet[first_empty_row, col_idx]

            # Insert the value
            if value != "":
                new_cell.set_value(value)

            # Copy style from upper cell
            if first_empty_row > 0:
                old_cell = sheet[first_empty_row - 1, col_idx]
                if old_cell.style_name is not None:  # Default format is None
                    new_cell.style_name = old_cell.style_name

            if col_idx == 2:
                # Force the format of the data
                new_cell.set_value(value, value_type="date")

            if col_idx == 3:
                new_cell.formula = f'of:=HYPERLINK("{self.exp_id}/"; "{self.exp_id}")'
                new_cell.style_name = "Hyperlink"

        # Save the OpenDocument
        doc.backup = False
        doc.save()

    def closeEvent(self, event):

        print("\nClosing DAQ Viewer")

        if not self.xClose:
            # Cleanup DAQ tasks
            for task in self.dev_comunicator.AcquisitionTasks:
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

    DAQ_TASKS = [
        {
            "NAME": "Dev1",
            "SAMPLE_RATE": 10000,

            "DAQ_CHANNELS":{
                "Voltage": {"port": "Dev1/ai3", "port_config": DAQmx_Val_Diff, "conversion_factor": None},
                # "Current": {"port": "Dev1/ai2", "port_config": DAQmx_Val_RSE, "conversion_factor": 1},
            },

            # "TRIGGER_SOURCE": "PFI0",
            "TRIGGER_SOURCE": None,

            "TYPE": "analog"
        },

        {
            "NAME": "Dev2",
            "SAMPLE_RATE": 10000,

            "DAQ_CHANNELS":{
                # "LinMot_Enable": {"port":"Dev2/ai0", "port_config":DAQmx_Val_RSE, "conversion_factor": None},
                # "LinMot_Up_Down": {"port":"Dev2/ai1", "port_config":DAQmx_Val_RSE, "conversion_factor": None}
                "LinMot_Enable": {"port":"Dev2/port0/line0", "port_config":None, "conversion_factor": None},
                "LinMot_Up_Down": {"port":"Dev2/port0/line1", "port_config":None, "conversion_factor": None}
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
    tribo_lab = True
    if debug:
        if tribo_lab:
            exp_dir = r"C:\Users\mmartic\Desktop\RogerTest"
        else:
            exp_dir = r"C:\Users\rpieres\Desktop\Test"
        tribu_id = "PDMSvsNylon"
        rload_id = "10"
    else:
        exp_dir = None
        tribu_id = None
        rload_id = None

    window = AcquisitionProgram(DAQ_TASKS,
                                automatic_mode=False,
                                RESISTANCE_DATA=resistance_list,
                                measure_time=1,
                                exp_dir=exp_dir,
                                tribu_id=tribu_id,
                                rload_id=rload_id)
    window.show()
    sys.exit(app.exec_())
