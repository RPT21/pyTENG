from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from ClassStructures.RaspberryInterface import RaspberryInterface
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

        self.start_acquisition_signal.connect(self.start_acquisition)
        self.stop_acquisition_signal.connect(self.stop_acquisition)

        # DAQ Analog Task
        self.AcquisitionTasks = []
        for n, task in enumerate(self.mainWindow.CHANNELS):
            if task["TYPE"] == "analog":
                self.AcquisitionTasks.append(AnalogRead(PLOT_BUFFER=self.mainWindow.plot_buffer,
                                    BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                                    SIGNAL_SELECTOR=None,
                                    BUFFER_SIZE=self.mainWindow.BUFFER_SIZE,
                                    CHANNELS=task["DAQ_CHANNELS"],
                                    SAMPLE_RATE=self.mainWindow.SAMPLE_RATE,
                                    SAMPLES_PER_CALLBACK=self.mainWindow.SAMPLES_PER_CALLBACK,
                                    AcquisitionProgramReference=self.mainWindow,
                                    TRIGGER_SOURCE=task["TRIGGER_SOURCE"]))
            elif task["TYPE"] == "digital":
                self.AcquisitionTasks.append(DigitalRead(PLOT_BUFFER=self.mainWindow.plot_buffer,
                                                        BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                                                        SIGNAL_SELECTOR=None,
                                                        BUFFER_SIZE=self.mainWindow.BUFFER_SIZE,
                                                        CHANNELS=task["DAQ_CHANNELS"],
                                                        SAMPLE_RATE=self.mainWindow.SAMPLE_RATE,
                                                        SAMPLES_PER_CALLBACK=self.mainWindow.SAMPLES_PER_CALLBACK,
                                                        AcquisitionProgramReference=self.mainWindow,
                                                        TRIGGER_SOURCE=task["TRIGGER_SOURCE"]))
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

    @pyqtSlot()
    def start_acquisition(self, iteration=0):

        if self.is_rb_connected:

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
                    self.mainWindow.error_flag = False
                    break
                elif status_bit_0 == 0 and status_bit_1 == 1:
                    # Error code
                    self.DO_task_PrepareRaspberry.set_line(0)
                    if iteration == 0:
                        print("\033[91mError, impossible to prepare raspberry to record, resetting Codesys, please wait... \033[0m")
                        self.raspberry.reset_codesys()
                        self.mainWindow.error_flag = True
                        self.start_acquisition(iteration = 1)
                        return
                    else:
                        print("\033[91mError, Raspberry is having an issue, check disk space or codesys CSV invalid license error\033[0m")
                        break
                else:
                    # Error code
                    self.DO_task_PrepareRaspberry.set_line(0)
                    if iteration == 0:
                        print("\033[91mError, EtherCAT bus is not working, resetting Codesys, please wait...\033[0m")
                        self.raspberry.reset_codesys()
                        self.mainWindow.error_flag = True
                        self.start_acquisition(iteration = 1)
                        return
                    else:
                        print("\033[91mError, LinMot is not responding, check if the firmware is turned on\033[0m")
                        break

                # Wait time
                time.sleep(0.1)

            if loop_counter >= max_iter:
                self.DO_task_PrepareRaspberry.set_line(0)
                print("\033[91mError loop counter overflow, Raspberry is not responding\033[0m")
                return

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
        if self.is_rb_connected and not self.mainWindow.error_flag:

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
                self.mainWindow.error_flag = True
                print("\033[91mError loop counter overflow, Raspberry is not responding\033[0m")

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
            if self.is_rb_connected:
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
        if self.is_rb_connected:
            self.raspberry.remove_files_with_extension(self.rb_remote_path)

        # Reset xRecording
        self.mainWindow.xRecording[0] = False

        # Send the stop acquisition return signal
        self.mainWindow.stop_acquisition_return_signal.emit()