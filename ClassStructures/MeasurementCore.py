import os
import shutil
import copy
import json
from datetime import datetime

from PyQt5.QtWidgets import (QPushButton, QVBoxLayout, QWidget,
                             QLabel, QSpinBox, QHBoxLayout, QFileDialog, QGroupBox, QMessageBox, QDesktopWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QElapsedTimer, pyqtSlot

from ClassStructures.BufferProcessor import BufferProcessor
from ClassStructures.DeviceCommunicator import DeviceCommunicator
from ClassStructures.AcquisitionGraph import ChannelSelectorComboBox, AcquisitionGraph
from ClassStructures.ExpConfigWindow import ExpConfigWindow
from ClassStructures.DAQProfilesWindow import DAQProfilesWindow
from ClassStructures.MetadataInterface import MetadataInterface
from utils.ImportantFunctions import CSV_merge

from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)

def _default_daq_task(task_type="analog"):
    return {
        "NAME": "New Task",
        "SAMPLE_RATE": 10000,
        "DAQ_CHANNELS": {
            "Channel 1": {
                "port": "",
                "port_config": DAQmx_Val_Diff if task_type == "analog" else None,
                "conversion_source": "none",
                "conversion_factor": None,
                "keithley_sense": "none",
            }
        },
        "TRIGGER_SOURCE": None,
        "TYPE": task_type,
    }

def _normalize_daq_profiles_source(daq_profiles):
    if daq_profiles is None:
        return {"Default": [_default_daq_task()]}

    if isinstance(daq_profiles, str):
        if not os.path.isfile(daq_profiles):
            raise FileNotFoundError(f"DAQ_PROFILES file not found: {daq_profiles}")
        with open(daq_profiles, "r", encoding="utf-8") as handle:
            daq_profiles = json.load(handle)

    if not isinstance(daq_profiles, dict):
        raise ValueError("DAQ_PROFILES must be None, a non-empty dict, or a path to a JSON file containing profiles.")

    return daq_profiles

class AcquisitionProgram(QWidget):

    trigger_acquisition_signal = pyqtSignal()
    start_acquisition_return_signal = pyqtSignal()
    stop_acquisition_return_signal = pyqtSignal()
    update_button_signal = pyqtSignal()

    def __init__(self,
                 METADATA_COLUMNS,
                 DAQ_PROFILES=None,
                 automatic_mode=False,
                 RESISTANCE_DATA=None,
                 exp_dir=None,
                 tribu_id=None,
                 SampleIdTriboNeg=None,
                 SampleIdTriboPos=None,
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
                 RelayCodeLines="Dev1/port0/line0:5",
                 use_raspberry=True,
                 use_keithley=True,
                 keithley_resource_name=None):

        super().__init__(parent)
        self.setWindowTitle("TENG Acquisition Software")
        self.layout = QVBoxLayout(self)
        self.setMinimumSize(1100, 900)
        self.center()  # Call the center function to center the window on the screen
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
        self.use_raspberry = use_raspberry
        self.use_keithley = use_keithley

        # ---------------- CONFIG ----------------

        # DAQ acquisition parameters
        self.DAQ_USB_TRANSFER_FREQUENCY = DAQ_USB_TRANSFER_FREQUENCY
        self.BUFFER_SAVING_TIME_INTERVAL = BUFFER_SAVING_TIME_INTERVAL
        self.ACQUISITION_PARAMS = {}
        self.METADATA_COLUMNS = METADATA_COLUMNS
        self.measure_time = measure_time

        # Initialize DAQ profiles from None / dict / JSON file path.
        self.daq_profiles = _normalize_daq_profiles_source(DAQ_PROFILES)
        self.active_daq_profile_name = "Default" if "Default" in self.daq_profiles else next(
            iter(self.daq_profiles.keys()))

        # Plot parameters
        self.TimeWindowLength = TimeWindowLength
        self.refresh_rate = int((1 / ScreenRefreshFrequency * 1000))  # Convert to milliseconds for QTimer

        self.DAQ_TASKS = copy.deepcopy(self.daq_profiles[self.active_daq_profile_name])
        self.DAQ_TASKS_METADATA = copy.deepcopy(self.DAQ_TASKS)

        self.automatic_mode = automatic_mode
        self.error_flag = False
        self.RESISTANCE_DATA = RESISTANCE_DATA
        self.iterations = 0
        self.iteration_index = 0
        self.DAQ_CODE = DAQ_CODE
        self.xClose = False
        self.mainWindowButtons = mainWindowButtons
        self.mainWindowParamGroups = mainWindowParamGroups
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

        # Manage TribuId via METADATA_COLUMNS.
        if tribu_id:
            if not isinstance(tribu_id, str):
                tribu_id = str(tribu_id)
            # If provided as parameter, set the live value in METADATA_COLUMNS
            self.METADATA_COLUMNS["TribuId"]["value"] = tribu_id
            self.tribu_id = tribu_id
        else:
            # Read current value from METADATA_COLUMNS
            self.tribu_id = self.METADATA_COLUMNS["TribuId"]["value"]

        # Manage SampleIdTriboNeg via METADATA_COLUMNS.
        if SampleIdTriboNeg:
            if not isinstance(SampleIdTriboNeg, str):
                SampleIdTriboNeg = str(SampleIdTriboNeg)
            # If provided as parameter, set the live value in METADATA_COLUMNS
            self.METADATA_COLUMNS["SampleIdTriboNeg"]["value"] = SampleIdTriboNeg
            self.SampleIdTriboNeg = SampleIdTriboNeg
        else:
            # Read current value from METADATA_COLUMNS
            self.SampleIdTriboNeg = self.METADATA_COLUMNS["SampleIdTriboNeg"]["value"]

        # Manage SampleIdTriboPos via METADATA_COLUMNS.
        if SampleIdTriboPos:
            if not isinstance(SampleIdTriboPos, str):
                SampleIdTriboPos = str(SampleIdTriboPos)
            # If provided as parameter, set the live value in METADATA_COLUMNS
            self.METADATA_COLUMNS["SampleIdTriboPos"]["value"] = SampleIdTriboPos
            self.SampleIdTriboPos = SampleIdTriboPos
        else:
            # Read current value from METADATA_COLUMNS
            self.SampleIdTriboPos = self.METADATA_COLUMNS["SampleIdTriboPos"]["value"]

        # Manage RloadId via METADATA_COLUMNS.
        if rload_id:
            if not isinstance(rload_id, str):
                rload_id = str(rload_id)
            # If provided as parameter, set the live value in METADATA_COLUMNS
            self.METADATA_COLUMNS["RloadId"]["value"] = rload_id
            self.rload_id = rload_id
        else:
            if not self.automatic_mode:
                # Read current value from METADATA_COLUMNS
                self.rload_id = self.METADATA_COLUMNS["RloadId"]["value"]
            else:
                self.rload_id = None

        ### ---------------- UI ELEMENTS ---------------- ###

        # Acquisition control button:
        self.acquisition_button = QPushButton("START LinMot")
        self.acquisition_button.setObjectName("primaryAction")
        self.acquisition_button.clicked.connect(self.trigger_acquisition)

        # Timer UI elements — days / hours / minutes / seconds
        self.timer_label = QLabel("Duration:")
        self.timer_spinbox_days = QSpinBox()
        self.timer_spinbox_hours = QSpinBox()
        self.timer_spinbox_minutes = QSpinBox()
        self.timer_spinbox_seconds = QSpinBox()
        self.timer_spinbox_days.setRange(0, 365)
        self.timer_spinbox_hours.setRange(0, 23)
        self.timer_spinbox_minutes.setRange(0, 59)
        self.timer_spinbox_seconds.setRange(0, 59)
        self.timer_spinbox_days.setSuffix(" d")
        self.timer_spinbox_hours.setSuffix(" h")
        self.timer_spinbox_minutes.setSuffix(" m")
        self.timer_spinbox_seconds.setSuffix(" s")
        for sb in (self.timer_spinbox_days, self.timer_spinbox_hours,
                   self.timer_spinbox_minutes, self.timer_spinbox_seconds):
            sb.setFixedWidth(72)
        # Set default value from measure_time (seconds)
        _d, _rem = divmod(measure_time, 86400)
        _h, _rem = divmod(_rem, 3600)
        _m, _s = divmod(_rem, 60)
        self.timer_spinbox_days.setValue(_d)
        self.timer_spinbox_hours.setValue(_h)
        self.timer_spinbox_minutes.setValue(_m)
        self.timer_spinbox_seconds.setValue(_s)
        self.countdown_display = QLabel("Remaining time: -")
        self.countdown_display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.duration = QHBoxLayout()
        self.duration.addWidget(self.timer_label)
        self.duration.addWidget(self.timer_spinbox_days)
        self.duration.addWidget(self.timer_spinbox_hours)
        self.duration.addWidget(self.timer_spinbox_minutes)
        self.duration.addWidget(self.timer_spinbox_seconds)

        # Timer setup
        self.measurement_timer = QTimer()
        self.measurement_timer.timeout.connect(self.update_countdown)
        self.remaining_seconds = 0
        self.should_save_data = False
        self._elapsed_timer = QElapsedTimer()

        # Buffer processor and thread for each DAQ Task
        self.buffer_processors = []
        self.thread_savers = []
        for n, task in enumerate(self.DAQ_TASKS):
            self.buffer_processors.append(BufferProcessor(TASK=task, mainWindowReference=self))
            self.thread_savers.append(QThread())
            self.buffer_processors[n].moveToThread(self.thread_savers[n])
            self.thread_savers[n].start()

        # Raspberry Communicator + DAQ Analog Task (2 threads):
        self.dev_communicator = DeviceCommunicator(mainWindowReference=self,
                                                  RelayCodeTask=RelayCodeTask,
                                                  LinMotTriggerTask=LinMotTriggerTask,
                                                  LinMotTriggerLine=LinMotTriggerLine,
                                                  PrepareRaspberryLine=PrepareRaspberryLine,
                                                  RaspberryStatus_0_Line=RaspberryStatus_0_Line,
                                                  RaspberryStatus_1_Line=RaspberryStatus_1_Line,
                                                  RelayCodeLines=RelayCodeLines,
                                                  keithley_resource_name=keithley_resource_name)

        self.thread_communicator = QThread()
        self.dev_communicator.moveToThread(self.thread_communicator)
        self.thread_communicator.start()

        # Metadata Interface
        self.MetadataInterface = MetadataInterface(mainWindowReference=self)

        # Signal management
        self.trigger_acquisition_signal.connect(self.trigger_acquisition)
        self.start_acquisition_return_signal.connect(self.start_acquisition_return)
        self.stop_acquisition_return_signal.connect(self.stop_acquisition_return)
        self.update_button_signal.connect(self.update_button)

        # Acquisition Graph
        self.plot_widget = AcquisitionGraph(self.TimeWindowLength)

        # Signal Selector
        self.signal_selector = ChannelSelectorComboBox(self.DAQ_TASKS, AcquisitionGraphReference=self.plot_widget)

        # Button to open Experiment Configuration Editor
        self.ExpConfigWindow = ExpConfigWindow(METADATA_COLUMNS=self.METADATA_COLUMNS, parent=self)
        self.edit_experiment_configuration = QPushButton("Edit Experiment Parameters")
        self.edit_experiment_configuration.clicked.connect(self.open_ExpConfigWindow)

        # Button to open DAQ profiles editor
        self.DAQProfilesWindow = DAQProfilesWindow(DAQ_PROFILES=self.daq_profiles, main_window_reference=self)
        self.edit_daq_profiles_button = QPushButton("Edit DAQ Profiles")
        self.edit_daq_profiles_button.clicked.connect(self.open_DAQProfilesWindow)

        # Text Label to know the active DAQ profile
        self.daq_profile_label = QLabel(f"Active DAQ profile: {self.active_daq_profile_name}")
        self.daq_profile_label.setObjectName("ProfileLabel")

        # Plot update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.plot_widget.update_plot)
        self.timer.start(self.refresh_rate)

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
        settings_button_row.addWidget(self.edit_experiment_configuration)
        settings_button_row.addWidget(self.edit_daq_profiles_button)
        settings_button_row.addStretch(1)
        settings_layout.addLayout(settings_button_row)
        settings_layout.addWidget(self.daq_profile_label)

        acquisition_box = QGroupBox("Acquisition")
        acquisition_layout = QHBoxLayout(acquisition_box)
        acquisition_layout.setContentsMargins(12, 18, 12, 12)
        acquisition_layout.setSpacing(12)
        acquisition_left = QVBoxLayout()
        acquisition_left.addWidget(self.acquisition_button)
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

        self.plot_widget.update_DAQ_Plot_Buffer()

        if self.automatic_mode:
            print("Starting acquisition in automatic mode.")
            self.trigger_acquisition()

    def center(self):
        # Get the screen geometry
        screen_rect = QDesktopWidget().availableGeometry()
        screen_center = screen_rect.center()

        # Calculate the position of the window in the screen based on the window geometry
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen_center)

        # Mover the window to this position
        self.move(window_rect.topLeft())

    def open_ExpConfigWindow(self):
        self.ExpConfigWindow.exec_()

    def open_DAQProfilesWindow(self):
        self.DAQProfilesWindow.exec_()

    @pyqtSlot(dict)
    def ask_reset_codesys(self, dictionary):
        reply = QMessageBox.question(
            self,
            dictionary["title"],
            dictionary["message"],
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        dictionary["result"] = reply

    @pyqtSlot(str)
    def show_raspberry_error(self, txt):
        QMessageBox.critical(self, "Raspberry Error", txt)

    def _sync_active_profile_label(self):
        self.daq_profile_label.setText(f"Active DAQ profile: {self.active_daq_profile_name}")

    def _close_runtime_daq_resources(self):

        # Disconnect plotter from the Acquisition Graph to avoid errors when closing DAQ tasks
        self.plot_widget.flush_screen()

        # Remove Acquisition Tasks
        for task in self.dev_communicator.AcquisitionTasks:
            task.StopTask()
            task.ClearTask()

        # Remove all created files
        for processor in self.buffer_processors:
            if processor.file_handle is not None:
                processor.remove_file()

        # Remove buffer save threads
        for thread in self.thread_savers:
            thread.quit()
            thread.wait()

        # Clear all Acquisition Tasks and Buffer Processors
        self.dev_communicator.AcquisitionTasks.clear()
        self.buffer_processors.clear()
        self.thread_savers.clear()

    def _refresh_signal_selector(self, preferred_label=None):
        self.signal_selector.rebuild_signal_selector(self.DAQ_TASKS)
        self.plot_widget.update_DAQ_Plot_Buffer()

    def apply_daq_profile(self, profile_name):
        if profile_name not in self.daq_profiles:
            raise KeyError(f"Unknown DAQ profile '{profile_name}'.")

        if self.moveLinMot[0]:
            raise RuntimeError("Stop the acquisition before applying a new DAQ profile.")

        self._close_runtime_daq_resources()

        self.DAQ_TASKS = copy.deepcopy(self.daq_profiles[profile_name])
        self.DAQ_TASKS_METADATA = copy.deepcopy(self.DAQ_TASKS)

        try:
            self.buffer_processors = []
            self.thread_savers = []

            for task in self.DAQ_TASKS:
                processor = BufferProcessor(TASK=task, mainWindowReference=self)
                self.buffer_processors.append(processor)
                thread = QThread()
                self.thread_savers.append(thread)
                processor.moveToThread(thread)
                thread.start()

            self.dev_communicator.rebuild_acquisition_tasks()
            self._refresh_signal_selector()

        except Exception as e:
            self._close_runtime_daq_resources()
            raise Exception(f"Error while applying DAQ profile '{profile_name}': {e}")

        self.active_daq_profile_name = profile_name
        self._sync_active_profile_label()
        print(f"Succesfully applied DAQ profile '{profile_name}'.")

    def _daq_tasks_require_keithley(self):
        """Check if any channel in DAQ_TASKS requires Keithley conversion factor resolution.

        Returns:
            bool: True if any channel has conversion_source='keithley', False otherwise.
        """
        for task in self.DAQ_TASKS:
            for channel_name, channel_config_data in task.get("DAQ_CHANNELS", {}).items():
                # channel_config_data might be [config_dict, index] after DaqInterface initialization
                if isinstance(channel_config_data, list):
                    channel_config = channel_config_data[0]
                else:
                    channel_config = channel_config_data

                if channel_config.get("conversion_source", "").strip().lower() == "keithley":
                    return True
        return False

    def update_countdown(self):

        if self.dev_communicator.raspberry:
            # It takes aprox 1 ms to read the status bits
            status_bit_0 = self.dev_communicator.DI_task_Raspberry_status_0.read_line()
            status_bit_1 = self.dev_communicator.DI_task_Raspberry_status_1.read_line()

            if not (status_bit_0 == 1 and status_bit_1 == 0):
                if not self.error_flag:
                    # An error has occurred during the data acquisition
                    print(f"\033[91mError, during the acquisition, the Raspberry sent an error code:\033[0m",
                          f"{status_bit_0}{status_bit_1}")
                    self.error_flag = True
                    self.trigger_acquisition()
            
        if not self.error_flag:
            elapsed_s = self._elapsed_timer.elapsed() / 1000.0  # ms → s
            self.remaining_seconds = max(0, self._measure_time_target - int(elapsed_s))

            if self.remaining_seconds > 0 and self.moveLinMot[0]:
                self.countdown_display.setText(f"Remaining time: {self._format_remaining(self.remaining_seconds)}")
            else:
                self.measurement_timer.stop()
                self._elapsed_timer.invalidate()
                self.countdown_display.setText("Remaining time: -")
                self.should_save_data = True
                self.trigger_acquisition()

    def _get_duration_seconds(self):
        """Return the total duration in seconds from the d/h/m/s spinboxes."""
        return (self.timer_spinbox_days.value() * 86400 +
                self.timer_spinbox_hours.value() * 3600 +
                self.timer_spinbox_minutes.value() * 60 +
                self.timer_spinbox_seconds.value())

    @staticmethod
    def _format_remaining(seconds):
        """Format an integer number of seconds as DD:HH:MM:SS or HH:MM:SS."""
        seconds = max(0, int(seconds))
        d, rem = divmod(seconds, 86400)
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        if d > 0:
            return f"{d}d {h:02d}:{m:02d}:{s:02d}"
        return f"{h:02d}:{m:02d}:{s:02d}"

    @pyqtSlot()
    def start_acquisition_return(self):

        if not self.error_flag:
            self._measure_time_target = self._get_duration_seconds()
            self.measure_time = self._measure_time_target
            self.remaining_seconds = self._measure_time_target
            self._elapsed_timer.start()
            self.countdown_display.setText(f"Remaining time: {self._format_remaining(self.remaining_seconds)}")
            self.measurement_timer.start(100)  # 100 ms
            self.should_save_data = False

            # Assign the plotter to the selected signal
            self.plot_widget.update_DAQ_Plot_Buffer()

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
        self.plot_widget.flush_screen()

        # Close the opened files
        for processor in self.buffer_processors:
            processor.close_file()

        metadata_error_code = 0
        if not self.error_flag:
            if self.should_save_data:

                # Convert the DAQ binary files to pandas dataframes
                for processor in self.buffer_processors:
                    processor.Binary_to_Pickle()

                # Merge the LinMot CSV files
                if self.dev_communicator.raspberry:
                    self.motor_file = CSV_merge(folder_path=self.local_path[0], exp_id=self.exp_id)
                else:
                    self.motor_file = ""

                # Save the metadata
                experiment_metadata = self.MetadataInterface.build_experiment_metadata()
                metadata_error_code = self.MetadataInterface.save_metadata(experiment_metadata)

                if metadata_error_code == 0:
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

        # If no error and user has not aborted the measure, delete only temporal files
        if not self.error_flag and self.should_save_data and metadata_error_code == 0:
            for processor in self.buffer_processors:
                processor.remove_file()
        else:
            # Delete all files
            shutil.rmtree(self.local_path[0])

    def update_button(self):
        self.acquisition_button.setText("STOP LinMot" if self.moveLinMot[0] else "START LinMot")

    @pyqtSlot()
    def trigger_acquisition(self):

        if self.sender() == self.acquisition_button and self.automatic_mode:
            print("Automatic mode has been disabled, stopping acquisition.")
            self.automatic_mode = False

        if self.error_flag:
            if self.sender() == self.acquisition_button:
                self.error_flag = False
            else:
                # STOP ADQUISITION
                self.measurement_timer.stop()
                self.countdown_display.setText("Remaining time: -")
                self.dev_communicator.stop_acquisition_signal.emit()
                print("Stopped acquisition due to an error.")
                return

        if self.automatic_mode:
            print(f"Starting the iteration {self.iteration_index} of {self.iterations}")

        if self.moveLinMot[0]:
            # STOP ADQUISITION
            self.measurement_timer.stop()
            self.countdown_display.setText("Remaining time: -")
            self.dev_communicator.stop_acquisition_signal.emit()
        else:
            # START ADQUISITION
            if self.automatic_mode:
                # automatic mode: take rload from RESISTANCE_DATA and write it into the Parameter Tree
                self.rload_id = self.RESISTANCE_DATA[self.iteration_index]["RLOAD_ID"]
                p = self.ExpConfigWindow.metadata_param_tree.param('RloadId')
                if p is not None:
                    p.setValue(self.rload_id)
            else:
                # manual mode: read rload_id from the Parameter Tree (must not be empty)
                p_RloadId = self.ExpConfigWindow.metadata_param_tree.param('RloadId')
                if p_RloadId is not None:
                    self.rload_id = p_RloadId.value()
                else:
                    self.rload_id = None

            if not self.rload_id:
                QMessageBox.critical(self, "Missing RloadId",
                                     "RloadId is required. Open 'Edit Experiment Defaults' and set RloadId in the Parameter Tree.")
                print("\nNo RloadId found in parameter tree (ExpConfigWindow).")
                return

            # Ensure tribu_id is available from the Parameter Tree (must not be empty)
            pTribuId = self.ExpConfigWindow.metadata_param_tree.param('TribuId')
            if pTribuId is not None:
                self.tribu_id = pTribuId.value()
            else:
                self.tribu_id = None

            # Ensure tribu_id is available from the Parameter Tree (must not be empty)
            SampleIdTriboPos = self.ExpConfigWindow.metadata_param_tree.param('SampleIdTriboPos')
            if SampleIdTriboPos is not None:
                self.SampleIdTriboPos = SampleIdTriboPos.value()
            else:
                self.SampleIdTriboPos = None

            # Ensure tribu_id is available from the Parameter Tree (must not be empty)
            SampleIdTriboNeg = self.ExpConfigWindow.metadata_param_tree.param('SampleIdTriboNeg')
            if SampleIdTriboNeg is not None:
                self.SampleIdTriboNeg = SampleIdTriboNeg.value()
            else:
                self.SampleIdTriboNeg = None

            if not self.tribu_id:
                QMessageBox.critical(self, "Missing TribuId",
                                     "TribuId is required. Open 'Edit Experiment Parameters' and set TribuId in the Parameter Tree.")
                print("\nNo TribuId found in parameter tree (ExpConfigWindow).")
                return

            if not self.SampleIdTriboPos:
                QMessageBox.critical(self, "Missing SampleIdTriboPos",
                                     "SampleIdTriboPos is required. Open 'Edit Experiment Parameters' and check the Parameter Tree.")
                print("\nNo SampleIdTriboPos found in parameter tree (ExpConfigWindow).")
                return

            if not self.SampleIdTriboNeg:
                QMessageBox.critical(self, "Missing SampleIdTriboNeg",
                                     "SampleIdTriboNeg is required. Open 'Edit Experiment Parameters' and check the Parameter Tree.")
                print("\nNo SampleIdTriboNeg found in parameter tree (ExpConfigWindow).")
                return

            # Check if Keithley is required but not available
            if self._daq_tasks_require_keithley():
                if not self.dev_communicator.keithley:
                    error_msg = (
                        "One or more channels require Keithley conversion factor resolution, "
                        "but Keithley is not available.\n\n"
                        "Please:\n"
                        "1. Ensure 'use_keithley=True' is set\n"
                        "2. Verify Keithley VISA resource name is correctly configured\n"
                        "3. Check that Keithley device is powered on and connected"
                    )
                    QMessageBox.critical(self, "Keithley Connection Error", error_msg)
                    print(f"\033[91m{error_msg}\033[0m")
                    return

            self.date_now = datetime.now().strftime("%d%m%Y_%H%M%S")
            self.exp_id = f"{self.date_now}-{self.rload_id}"

            # Create necessary folders and define the saving path
            # Structure: RawData/{TribuId}/{self.SampleIdTriboNeg}-{self.SampleIdTriboPos}/{date}-{RloadId}/
            tribu_folder_path = os.path.join(self.exp_dir, "RawData", self.tribu_id)

            # Check if TribuId folder exists; if not, ask for confirmation
            if not os.path.isdir(tribu_folder_path):
                reply = QMessageBox.question(
                    self,
                    "Create New TribuId Folder",
                    f"The TribuId folder '{self.tribu_id}' does not exist.\n\n"
                    f"Do you want to create and use this folder?\n\n"
                    f"Path: {tribu_folder_path}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.No:
                    print(f"Creation of TribuId folder '{self.tribu_id}' cancelled by user.")
                    return

            self.local_path[0] = os.path.join(tribu_folder_path, f"{self.SampleIdTriboNeg}-{self.SampleIdTriboPos}",
                                              self.exp_id)

            os.makedirs(self.local_path[0], exist_ok=True)  # Note: Windows is letter case-insensitive

            # Open the files to save the data
            for processor in self.buffer_processors:
                processor.open_file()

            self.dev_communicator.start_acquisition_signal.emit()

    def closeEvent(self, event):

        print("\nClosing DAQ Viewer")

        if not self.xClose:
            # Disconnect from Keithley if connected
            if self.dev_communicator.keithley is not None:
                try:
                    self.dev_communicator.keithley.disconnect()
                except Exception as e:
                    print(f"Warning: Failed to disconnect from Keithley: {e}")
                self.dev_communicator.keithley = None

            # Cleanup DAQ tasks
            for task in self.dev_communicator.AcquisitionTasks:
                task.StopTask()
                task.ClearTask()

            self.dev_communicator.DO_task_LinMotTrigger.set_line(0)
            if not self.LinMotTriggerTask:
                self.dev_communicator.DO_task_LinMotTrigger.StopTask()
                self.dev_communicator.DO_task_LinMotTrigger.ClearTask()

            self.dev_communicator.DO_task_RelayCode.set_lines([0, 0, 0, 0, 0, 0])
            if not self.RelayCodeTask:
                self.dev_communicator.DO_task_RelayCode.StopTask()
                self.dev_communicator.DO_task_RelayCode.ClearTask()

            self.dev_communicator.DO_task_PrepareRaspberry.set_line(0)
            self.dev_communicator.DO_task_PrepareRaspberry.StopTask()
            self.dev_communicator.DO_task_PrepareRaspberry.ClearTask()

            self.dev_communicator.DI_task_Raspberry_status_0.StopTask()
            self.dev_communicator.DI_task_Raspberry_status_0.ClearTask()

            self.dev_communicator.DI_task_Raspberry_status_1.StopTask()
            self.dev_communicator.DI_task_Raspberry_status_1.ClearTask()

            # Disconnect from Raspberry if connected
            if self.dev_communicator.raspberry:
                self.dev_communicator.raspberry.disconnect()

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
                self._set_group_readonly(param_group, readonly=False)

        # Use the accept() method of the class QCloseEvent to close the QWidget (if not desired use the ignore() method)
        event.accept()

    def _set_group_readonly(self, group, readonly=True):
        group.setReadonly(readonly)
        for child in group.children():
            if child.hasChildren():
                self._set_group_readonly(child, readonly)
            else:
                child.setReadonly(readonly)

    def showEvent(self, event):
        super().showEvent(event)
        if self.xClose:
            # Close the QWidget as soon as it is created adding in the event loop a QTimer event
            QTimer.singleShot(0, lambda: self.close())