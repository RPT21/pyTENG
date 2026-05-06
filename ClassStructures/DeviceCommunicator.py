from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMetaObject, Qt, Q_ARG
from PyQt5.QtWidgets import QMessageBox
from ClassStructures.RaspberryInterface import RaspberryInterface
from ClassStructures.KeithleyInterface import KeithleyInterface
from ClassStructures.DaqInterface import *
from PyDAQmx import DAQmxIsTaskDone, bool32
import time

class DeviceCommunicator(QObject):

    start_acquisition_signal = pyqtSignal()
    stop_acquisition_signal = pyqtSignal()

    def __init__(self, mainWindowReference, parent=None,
                 RelayCodeTask = None,
                 LinMotTriggerTask = None,
                 LinMotTriggerLine = "Dev1/port0/line7",
                 PrepareRaspberryLine = "Dev1/port0/line6",
                 RaspberryStatus_0_Line = "Dev1/port1/line0",
                 RaspberryStatus_1_Line = "Dev1/port1/line1",
                 RelayCodeLines = "Dev1/port0/line0:5",
                 keithley_resource_name=None):

        super().__init__(parent)

        self.mainWindow = mainWindowReference

        # Connect to Raspberry if desired:
        if self.mainWindow.use_raspberry:
            self.rb_hostname = "192.168.100.200"
            self.rb_port = 22
            self.rb_username = "TENG"
            self.rb_password = "raspberry"
            self.rb_remote_path = "/var/opt/codesys/PlcLogic/FTP_Folder"

            self.raspberry = RaspberryInterface(hostname=self.rb_hostname,
                                                port=self.rb_port,
                                                username=self.rb_username,
                                                password=self.rb_password)

            if not self.raspberry.connect():
                self.raspberry = None
                print("The program will work without using Raspberry Pi.")
        else:
            self.raspberry = None

        # Connect to Keithley if desired:
        if self.mainWindow.use_keithley:
            self.keithley = KeithleyInterface(resource_name=keithley_resource_name)
            try:
                device_id = self.keithley.connect(timeout_ms=5000)

                # After connecting to Keithley it is in remote mode and cannot be operated manually
                self.keithley.set_manual_control()

                print(f"Connected to Keithley: {device_id}")

            except Exception as exc:
                print(f"\033[91mError, impossible to connect to Keithley: {exc} \033[0m")
                print("The program will work without using Keithley.")
                self.keithley = None
        else:
            self.keithley = None

        if self.mainWindow.use_raspberry and self.mainWindow.use_keithley:
            if not self.raspberry and not self.keithley:
                txt = ("Keithley and Raspberry are not responding, check if they are turned on.\n\n"
                       "The software will work without using them.")
                QMetaObject.invokeMethod(self.mainWindow,
                                         "show_device_communicator_warning",
                                         Qt.ConnectionType.QueuedConnection,
                                         Q_ARG(str, txt)
                                         )

        elif self.mainWindow.use_raspberry:
            if not self.raspberry:
                txt = ("Raspberry is not responding, check if it is turned on.\n\n"
                       "The software will work without using Raspberry.")
                QMetaObject.invokeMethod(self.mainWindow,
                                         "show_device_communicator_warning",
                                         Qt.ConnectionType.QueuedConnection,
                                         Q_ARG(str, txt)
                                         )

        elif self.mainWindow.use_keithley:
            if not self.keithley:
                txt = ("Keithley is not responding, check if it is turned on.\n\n"
                       "The software will work without using Keithley.")
                QMetaObject.invokeMethod(self.mainWindow,
                                         "show_device_communicator_warning",
                                         Qt.ConnectionType.QueuedConnection,
                                         Q_ARG(str, txt)
                                         )

        self.start_acquisition_signal.connect(self.start_acquisition)
        self.stop_acquisition_signal.connect(self.stop_acquisition)

        # DAQ Analog Task
        self.AcquisitionTasks = []
        for n, task in enumerate(self.mainWindow.DAQ_TASKS):

            if task["TYPE"] == "analog":
                self.AcquisitionTasks.append(
                    AnalogRead(
                        TASK=task,
                        BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                        DAQ_USB_TRANSFER_FREQUENCY=self.mainWindow.DAQ_USB_TRANSFER_FREQUENCY,
                        BUFFER_SAVING_TIME_INTERVAL=self.mainWindow.BUFFER_SAVING_TIME_INTERVAL,
                        TimeWindowLength=self.mainWindow.TimeWindowLength,
                        AcquisitionProgramReference=self.mainWindow)
                )
            elif task["TYPE"] == "digital":
                self.AcquisitionTasks.append(
                    DigitalRead(
                        TASK=task,
                        BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                        DAQ_USB_TRANSFER_FREQUENCY=self.mainWindow.DAQ_USB_TRANSFER_FREQUENCY,
                        BUFFER_SAVING_TIME_INTERVAL=self.mainWindow.BUFFER_SAVING_TIME_INTERVAL,
                        TimeWindowLength=self.mainWindow.TimeWindowLength,
                        AcquisitionProgramReference=self.mainWindow)
                )
            else:
                raise Exception("Error the task TYPE is not analog neither digital")

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

    def rebuild_acquisition_tasks(self):
        self.AcquisitionTasks = []
        for n, task in enumerate(self.mainWindow.DAQ_TASKS):

            if task["TYPE"] == "analog":
                self.AcquisitionTasks.append(
                    AnalogRead(
                        TASK=task,
                        BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                        DAQ_USB_TRANSFER_FREQUENCY=self.mainWindow.DAQ_USB_TRANSFER_FREQUENCY,
                        BUFFER_SAVING_TIME_INTERVAL=self.mainWindow.BUFFER_SAVING_TIME_INTERVAL,
                        TimeWindowLength=self.mainWindow.TimeWindowLength,
                        AcquisitionProgramReference=self.mainWindow)
                )
            elif task["TYPE"] == "digital":
                self.AcquisitionTasks.append(
                    DigitalRead(
                        TASK=task,
                        BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                        DAQ_USB_TRANSFER_FREQUENCY=self.mainWindow.DAQ_USB_TRANSFER_FREQUENCY,
                        BUFFER_SAVING_TIME_INTERVAL=self.mainWindow.BUFFER_SAVING_TIME_INTERVAL,
                        TimeWindowLength=self.mainWindow.TimeWindowLength,
                        AcquisitionProgramReference=self.mainWindow)
                )
            else:
                raise Exception("Error the task TYPE is not analog neither digital")

    @pyqtSlot()
    def start_acquisition(self, iteration=0):

        # Resolve Keithley conversion factors before starting acquisition
        if self.keithley and not self.mainWindow.error_flag:
            try:
                self._resolve_keithley_conversion_factors()
            except Exception as exc:
                print(f"Failed to resolve Keithley conversion factors:\n{exc}")
                self.mainWindow.error_flag = True

        if self.raspberry and not self.mainWindow.error_flag:

            # Send a trigger to prepare the Raspberry to record data
            self.DO_task_PrepareRaspberry.set_line(1)

            loop_counter = 0
            max_iter = 10  # Wait time is 0.1, so it is 1 second

            while loop_counter < max_iter:
                status_bit_0 = self.DI_task_Raspberry_status_0.read_line()
                status_bit_1 = self.DI_task_Raspberry_status_1.read_line()

                if status_bit_0 == 0 and status_bit_1 == 0:
                    # Not responding
                    loop_counter += 1
                elif status_bit_0 == 1 and status_bit_1 == 0:
                    # OK code
                    print("Raspberry is ready to record data")
                    break
                elif status_bit_0 == 0 and status_bit_1 == 1:
                    # Error code
                    self.DO_task_PrepareRaspberry.set_line(0)
                    if iteration == 0:
                        dictionary = {"title": "Raspberry Connection Error",
                                      "message": "Impossible to prepare raspberry to record do you want to reset codesys and try again?",
                                      "result": None
                                      }
                        QMetaObject.invokeMethod(self.mainWindow,
                                                 "ask_reset_codesys",
                                                 Qt.ConnectionType.BlockingQueuedConnection,
                                                 Q_ARG(dict, dictionary)
                                                 )
                        if dictionary["result"] == QMessageBox.No:
                            print(f"Acquisition aborted")
                            self.mainWindow.error_flag = True
                            break

                        self.mainWindow.acquisition_button.setEnabled(False)
                        self.raspberry.reset_codesys()
                        self.start_acquisition(iteration = 1)
                        return
                    else:
                        txt = "Error, Raspberry is having an issue, check disk space or codesys CSV invalid license error"
                        QMetaObject.invokeMethod(self.mainWindow,
                                                 "show_raspberry_error",
                                                 Qt.ConnectionType.QueuedConnection,
                                                 Q_ARG(str, txt)
                                                 )
                        self.mainWindow.error_flag = True
                        break
                else:
                    # Error code
                    self.DO_task_PrepareRaspberry.set_line(0)
                    if iteration == 0:
                        dictionary = {"title":"Raspberry Connection Error",
                                      "message":"EtherCAT bus is not working, do you want to reset codesys and try again?",
                                      "result":None
                                      }
                        QMetaObject.invokeMethod(self.mainWindow,
                                                 "ask_reset_codesys",
                                                 Qt.ConnectionType.BlockingQueuedConnection,
                                                 Q_ARG(dict, dictionary)
                                                 )
                        if dictionary["result"] == QMessageBox.No:
                            print(f"Acquisition aborted")
                            self.mainWindow.error_flag = True
                            break

                        self.mainWindow.acquisition_button.setEnabled(False)
                        self.raspberry.reset_codesys()
                        self.start_acquisition(iteration = 1)
                        return
                    else:
                        txt = "Error, LinMot is not responding, check if the firmware is turned on"
                        QMetaObject.invokeMethod(self.mainWindow,
                                                 "show_raspberry_error",
                                                 Qt.ConnectionType.QueuedConnection,
                                                 Q_ARG(str, txt)
                                                 )
                        self.mainWindow.error_flag = True
                        break

                # Wait time
                time.sleep(0.1)

            if loop_counter >= max_iter:
                self.DO_task_PrepareRaspberry.set_line(0)
                self.mainWindow.error_flag = True
                txt = "Error, Raspberry is not responding, check if it is connected"
                QMetaObject.invokeMethod(self.mainWindow,
                                         "show_raspberry_error",
                                         Qt.ConnectionType.QueuedConnection,
                                         Q_ARG(str, txt)
                                         )

            if not self.mainWindow.acquisition_button.isEnabled():
                self.mainWindow.acquisition_button.setEnabled(True)

        if not self.mainWindow.error_flag:

            # Activate the relays
            if self.mainWindow.automatic_mode:
                self.DO_task_RelayCode.set_lines(self.mainWindow.RESISTANCE_DATA[self.mainWindow.iteration_index]["DAQ_CODE"])
            else:
                self.DO_task_RelayCode.set_lines(self.mainWindow.DAQ_CODE)

            # Start Acquisition Tasks
            self.mainWindow.moveLinMot[0] = True
            for task in self.AcquisitionTasks:
                task.index = 0
                task.StartTask()
            self.mainWindow.xRecording[0] = True

            # Do the LinMot trigger
            self.DO_task_LinMotTrigger.set_line(1)

        # Send the start acquisition return signal
        self.mainWindow.start_acquisition_return_signal.emit()

    @pyqtSlot()
    def stop_acquisition(self):

        self.DO_task_LinMotTrigger.set_line(0)
        self.DO_task_PrepareRaspberry.set_line(0)
        self.DO_task_RelayCode.set_lines([0,0,0,0,0,0])

        # Wait until raspberry has saved the LinMot_Enable = 0, then stop the DAQ Acquisition
        if self.raspberry and not self.mainWindow.error_flag:

            loop_counter = 0
            max_iter = 10  # Wait time is 0.1, so it is 1 second

            while loop_counter < max_iter:

                status_bit_0 = self.DI_task_Raspberry_status_0.read_line()
                status_bit_1 = self.DI_task_Raspberry_status_1.read_line()

                if status_bit_0 == 0 and status_bit_1 == 0:
                    # Raspberry returned to idle state
                    break

                # If not, it is still doing something
                loop_counter += 1

                # Wait time
                time.sleep(0.1)

            if loop_counter >= max_iter:
                if not self.mainWindow.error_flag:
                    self.mainWindow.error_flag = True
                    txt = "Error, Raspberry is not responding, check if it is connected"
                    QMetaObject.invokeMethod(self.mainWindow,
                                             "show_raspberry_error",
                                             Qt.ConnectionType.QueuedConnection,
                                             Q_ARG(str, txt)
                                             )

            # Wait time to let the DAQ measure LinMot_Enable = 0
            time.sleep(0.1)

        # Stop the acquisition
        self.mainWindow.moveLinMot[0] = False

        # Wait until all DAQ Tasks have stopped
        print("Waiting DAQ Tasks to stop ...")
        all_stopped = False
        done = bool32()
        while not all_stopped:
            all_stopped = True
            for task in self.AcquisitionTasks:
                DAQmxIsTaskDone(task.taskHandle, byref(done))
                if not done.value:
                    all_stopped = False
                    time.sleep(0.1)
                    break
        print("All tasks have stopped")

        # Flush plot buffers
        for task in self.AcquisitionTasks:
            task.plot_buffer.fill(np.nan)
        print("All plot buffers have been flushed")

        # Save the DAQ data and download the data from the raspberry if no error
        if not self.mainWindow.error_flag:

            # Save the DAQ data
            print("Saving the remaining data ...")
            for n, task in enumerate(self.AcquisitionTasks):
                if task.index != 0:

                    data = task.current_buffer[:task.index]

                    # In this case this thread will do the saving
                    self.mainWindow.buffer_processors[n].save_data(data)

                    task.index = 0

            # Save the Raspberry data
            if self.raspberry:
                self.raspberry.download_folder(self.rb_remote_path, local_path=self.mainWindow.local_path[0])

            # Continue with the next Resistance Load if the program is in automatic mode (and no error found)
            if self.mainWindow.automatic_mode:

                # Wait motor return to the origin position
                self.mainWindow.update_button_signal.emit()
                self.mainWindow.iteration_index += 1

                # Increase iteration_index
                if self.mainWindow.iteration_index <= self.mainWindow.iterations:
                    print("Waiting LinMot to return to origin position")
                    time.sleep(5)

        # Remove the Raspberry files to free disk space
        if self.raspberry:
            self.raspberry.remove_files_with_extension(self.rb_remote_path)

        # Reset xRecording
        self.mainWindow.xRecording[0] = False

        # Send the stop acquisition return signal
        self.mainWindow.stop_acquisition_return_signal.emit()

    def _resolve_keithley_conversion_factors(self):
        """Resolve Keithley mode channels by querying device range before acquisition.

        For each channel with conversion_source='keithley', reads the active measurement
        range and stores it as the numeric conversion_factor in the DAQ_TASKS and DAQ_TASKS_METADATA dict.
        """
        for task_idx, task in enumerate(self.mainWindow.DAQ_TASKS):
            for channel_name, channel_config_data in task.get("DAQ_CHANNELS", {}).items():
                # channel_config_data might be [config_dict, index] after DaqInterface initialization
                if isinstance(channel_config_data, list):
                    channel_config = channel_config_data[0]
                else:
                    channel_config = channel_config_data

                # Query range for each Keithley channel and update DAQ_TASKS and DAQ_TASKS_METADATA
                if channel_config.get("conversion_source", "").strip().lower() == "keithley":
                    keithley_sense = str(channel_config.get("keithley_sense", "none")).strip().lower() or "none"

                    # Obtain task name
                    task_name = task.get("NAME")

                    # Check that the sense is valid
                    if keithley_sense == "none":
                        raise Exception("Keithley 'none' sense is not supported, please specify a valid sense "
                                        "(e.g., 'current', 'voltage', etc.) in the channel configuration.")

                    try:
                        # Query the range that matches the configured measurement type
                        measurement_range = self.keithley.read_range(sense=keithley_sense, manual_control=False)
                        conversion_factor = self.keithley.get_conversion_factor_from_keithley(sense=keithley_sense,
                                                                                              manual_control=True)

                        # Update the DAQ_TASKS dict:
                        channel_config["conversion_factor"] = conversion_factor

                        # Also update DAQ_TASKS_METADATA list so it gets saved to the JSON sidecar
                        task_metadata = self.mainWindow.DAQ_TASKS_METADATA[task_idx]
                        channel_config_data_metadata = task_metadata["DAQ_CHANNELS"][channel_name]
                        channel_config_data_metadata["conversion_factor"] = conversion_factor

                        print(f"Resolved Keithley range for task '{task_name}' "
                              f"channel '{channel_name}' ({keithley_sense}): {measurement_range} -> "
                              f"conversion_factor = {conversion_factor}"
                              )
                    except Exception as exc:
                        raise RuntimeError(f"Failed to read Keithley range for channel '{channel_name}': {exc}")
