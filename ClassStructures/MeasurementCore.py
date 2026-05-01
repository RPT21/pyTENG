import os
import shutil
import copy
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QPushButton, QVBoxLayout, QWidget,
                             QLabel, QSpinBox, QHBoxLayout, QFileDialog, QInputDialog, QComboBox, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, pyqtSlot
from utils.ImportantFunctions import CSV_merge
from ClassStructures.BufferProcessor import BufferProcessor
from ClassStructures.DeviceCommunicator import DeviceCommunicator

from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def _get_daq_internal_buffer_size(task_sampling_rate):
    """
    Calculate the internal DAQ buffer size based on the task sampling rate.

    Rules:
    - 0-100 Hz: 1,000
    - 101-10,000 Hz: 10,000
    - 10,001-1,000,000 Hz: 100,000
    - >1,000,000 Hz: 1,000,000
    """
    if task_sampling_rate <= 100:
        return 1000
    elif task_sampling_rate <= 10000:
        return 10000
    elif task_sampling_rate <= 1000000:
        return 100000
    else:
        return 1000000

def _find_divisors(n):
    """Find all divisors of n, sorted"""
    divisors = set()
    for i in range(1, int(np.sqrt(n)) + 1):
        if n % i == 0:
            divisors.add(i)
            divisors.add(n // i)
    return sorted(divisors)

def _set_group_readonly(group, readonly=True):
    group.setReadonly(readonly)
    for child in group.children():
        if child.hasChildren():
            _set_group_readonly(child, readonly)
        else:
            child.setReadonly(readonly)


class ChannelSelectorComboBox(QComboBox):
    def value(self):
        return self.currentData()

# ---------------- INTERFACE AND PLOT  ----------------
class AcquisitionProgram(QWidget):

    trigger_acquisition_signal = pyqtSignal()
    start_acquisition_return_signal = pyqtSignal()
    stop_acquisition_return_signal = pyqtSignal()
    update_button_signal = pyqtSignal()
    
    def __init__(self,
                 DAQ_PROFILES,
                 METADATA_COLUMNS,
                 automatic_mode=False,
                 RESISTANCE_DATA=None,
                 exp_dir=None,
                 tribu_id=None,
                 rload_id=None,
                 DAQ_CODE=(0, 0, 0, 0, 0, 1),
                 measure_time=30,
                 DAQ_USB_TRANSFER_FREQUENCY=60,  # USB transfers per second (Hz)
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
        self.setMinimumSize(1180, 760)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        self.setStyleSheet("""
            QWidget { background: #f5f7fb; color: #1f2937; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
            QLabel#TitleLabel { font-size: 22px; font-weight: 700; color: #0f172a; }
            QLabel#ProfileLabel { font-size: 16px; font-weight: 700; color: #0f172a; }
            QLabel#SectionHint { color: #64748b; font-size: 11px; }
            QGroupBox { background: #ffffff; border: 1px solid #d7dde8; border-radius: 10px; margin-top: 12px; padding-top: 10px; font-size: 13px; font-weight: 600; color: #334155; }
            QGroupBox#PlotBox { background: #111827; border: 1px solid #1f2937; border-radius: 10px; margin-top: 12px; padding-top: 0px; font-size: 13px; font-weight: 600; color: #e5e7eb; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #334155; }
            QGroupBox#PlotBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #e5e7eb; }
            QPushButton { background: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 8px; padding: 7px 12px; min-height: 18px; font-size: 13px; }
            QPushButton:hover { background: #dbeafe; border-color: #93c5fd; }
            QPushButton:pressed { background: #bfdbfe; }
            QPushButton#primaryAction { background: #2563eb; color: white; border-color: #1d4ed8; font-weight: 600; }
            QPushButton#primaryAction:hover { background: #1d4ed8; }
            QComboBox { background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 5px 10px; min-height: 24px; font-size: 13px; }
            QComboBox::drop-down { border: 0; width: 24px; }
        """)

        # Define the moveLinmot bool: 
        # We use a list because a bool is not referenced when passed as an argument
        self.moveLinMot = [False]
        self.xRecording = [False]
        self.LinMotTriggerTask = LinMotTriggerTask
        self.RelayCodeTask = RelayCodeTask
        self.LinMotTriggerLine = LinMotTriggerLine
        self.PrepareRaspberryLine = PrepareRaspberryLine
        self.RaspberryStatus_0_Line = RaspberryStatus_0_Line
        self.RaspberryStatus_1_Line = RaspberryStatus_1_Line
        self.RelayCodeLines = RelayCodeLines

        # ---------------- CONFIG ----------------

        # DAQ acquisition parameters
        self.DAQ_USB_TRANSFER_FREQUENCY = DAQ_USB_TRANSFER_FREQUENCY
        self.BUFFER_SAVING_TIME_INTERVAL = BUFFER_SAVING_TIME_INTERVAL
        self.ACQUISITION_PARAMS = {}
        self.METADATA_COLUMNS = METADATA_COLUMNS
        self.measure_time = measure_time

        # Initialize DAQ profiles from provided mapping (profile_name -> list of DAQ task dicts)
        if not isinstance(DAQ_PROFILES, dict) or not DAQ_PROFILES:
            raise ValueError("DAQ_PROFILES must be a non-empty dict mapping profile names to DAQ task lists")
        self.daq_profiles = copy.deepcopy(DAQ_PROFILES)
        self.active_daq_profile_name = "Default" if "Default" in self.daq_profiles else next(iter(self.daq_profiles.keys()))
        initial_tasks = copy.deepcopy(self.daq_profiles[self.active_daq_profile_name])

        # Plot parameters
        self.TimeWindowLength = TimeWindowLength
        self.refresh_rate = int((1 / ScreenRefreshFrequency * 1000))  # Convert to milliseconds for QTimer

        # Calculate buffer sizes for each DAQ Task (from active profile)
        for task in initial_tasks:
            # Get internal DAQ buffer size based on total sampling rate
            internal_buffer_size = _get_daq_internal_buffer_size(task["SAMPLE_RATE"])

            # Calculate initial SAMPLES_PER_CALLBACK
            initial_samples_per_callback = int(task["SAMPLE_RATE"] / DAQ_USB_TRANSFER_FREQUENCY)

            # Find divisors of internal buffer size
            divisors_of_internal_buffer = _find_divisors(internal_buffer_size)

            # Pick the divisor closest to initial_samples_per_callback
            samples_per_callback = min(divisors_of_internal_buffer,
                                      key=lambda x: abs(x - initial_samples_per_callback))

            # Log the adjustment if it changed
            if samples_per_callback != initial_samples_per_callback:
                print(f"Task {task['NAME']}: Adjusted SAMPLES_PER_CALLBACK from {initial_samples_per_callback} to {samples_per_callback}")
                print(f"  Task sampling rate: {task["SAMPLE_RATE"]} Hz, DAQ Internal buffer size: {internal_buffer_size}")

            # Calculate other parameters
            callbacks_per_buffer = int(BUFFER_SAVING_TIME_INTERVAL * DAQ_USB_TRANSFER_FREQUENCY)
            plot_buffer_size = ((task["SAMPLE_RATE"] * TimeWindowLength) // samples_per_callback) * samples_per_callback

            self.ACQUISITION_PARAMS[task["NAME"]] = {
                'SAMPLES_PER_CALLBACK': samples_per_callback,
                'BUFFER_SIZE': samples_per_callback * callbacks_per_buffer,
                'PLOT_BUFFER_SIZE': plot_buffer_size,
                'INTERNAL_BUFFER_SIZE': internal_buffer_size,
            }

        self.DAQ_TASKS = initial_tasks
        self.DAQ_TASKS_METADATA = copy.deepcopy(initial_tasks)

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
        for task in self.DAQ_TASKS:
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

        ### ---------------- UI ELEMENTS ---------------- ###

        # Acquisition control button:
        self.button = QPushButton("START LinMot")
        self.button.setObjectName("primaryAction")
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
            for channel_name, channel_value in task["DAQ_CHANNELS"].items():
                total_tasks[f"{task['NAME']} - {channel_name}"] = channel_value

        # Signal Selector
        self.signal_selector = ChannelSelectorComboBox()
        self.signal_selector.setToolTip("Select the channel to display")
        self._populate_signal_selector(total_tasks)
        self.signal_selector.currentIndexChanged.connect(self._update_DAQ_Plot_Buffer)

        # Now we can assign the signal selector to the DAQs:
        for task in self.dev_comunicator.AcquisitionTasks:
            task.data_column_selector = self.signal_selector

        # Button to open experiment defaults editor (in separate dialog)
        self.edit_defaults_button = QPushButton("Edit Experiment Parameters")
        self.edit_defaults_button.clicked.connect(self.open_defaults_dialog)

        # Button to open DAQ profiles editor
        self.edit_daq_profiles_button = QPushButton("Edit DAQ Profiles")
        self.edit_daq_profiles_button.clicked.connect(self.open_daq_profiles_dialog)

        self.daq_profile_label = QLabel(f"Active DAQ profile: {self.active_daq_profile_name}")
        self.daq_profile_label.setObjectName("ProfileLabel")

        channel_box = QGroupBox("Channel Selection")
        channel_layout = QVBoxLayout(channel_box)
        channel_layout.setContentsMargins(12, 18, 12, 12)
        channel_layout.setSpacing(6)
        channel_layout.addWidget(self.signal_selector)

        settings_box = QGroupBox("Experiment Setup")
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.setContentsMargins(12, 18, 12, 12)
        settings_layout.setSpacing(8)
        settings_button_row = QHBoxLayout()
        settings_button_row.addWidget(self.edit_defaults_button)
        settings_button_row.addWidget(self.edit_daq_profiles_button)
        settings_button_row.addStretch(1)
        settings_layout.addLayout(settings_button_row)
        settings_layout.addWidget(self.daq_profile_label)

        acquisition_box = QGroupBox("Acquisition")
        acquisition_layout = QHBoxLayout(acquisition_box)
        acquisition_layout.setContentsMargins(12, 18, 12, 12)
        acquisition_layout.setSpacing(12)
        acquisition_left = QVBoxLayout()
        acquisition_left.addWidget(self.button)
        acquisition_left.addStretch(1)
        acquisition_right = QVBoxLayout()
        acquisition_right.addWidget(self.countdown_display)
        acquisition_right.addLayout(self.duration)
        acquisition_right.addStretch(1)
        acquisition_layout.addLayout(acquisition_left)
        acquisition_layout.addLayout(acquisition_right)

        plot_box = QGroupBox("")
        plot_box.setObjectName("PlotBox")
        plot_layout = QVBoxLayout(plot_box)
        plot_layout.setContentsMargins(12, 18, 12, 12)
        plot_layout.addWidget(self.plot_widget)

        # Add widgets to the layout (sorted from top to bottom)
        self.layout.addWidget(channel_box)
        self.layout.addWidget(settings_box)
        self.layout.addWidget(acquisition_box)
        self.layout.addWidget(plot_box)

        self._update_DAQ_Plot_Buffer()

        if self.automatic_mode:
            print("Starting acquisition in automatic mode.")
            self.trigger_acquisition()

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

    @pyqtSlot()
    def start_acquisition_return(self):

        if not self.error_flag:
            self.remaining_seconds = self.timer_spinbox.value()
            self.measure_time = self.timer_spinbox.value()
            self.countdown_display.setText(f"Remaining time: {self.remaining_seconds} s")
            self.measurement_timer.start(1000)  # 1 sec
            self.should_save_data = False

            # Assign the plotter to the selected signal
            selected = self.signal_selector.value()
            self.actual_plotter = selected[-2] if selected else None

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

                # Save the metadata
                experiment_metadata = self._build_experiment_metadata()
                error_code = self.save_metadata(experiment_metadata)

                if error_code == 0:
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
                _set_group_readonly(param_group, readonly=False)


        # Use the accept() method of the class QCloseEvent to close the QWidget (if not desired use the ignore() method)
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if self.xClose:
            # Close the QWidget as soon as it is created adding in the event loop a QTimer event
            QTimer.singleShot(0, self.close)