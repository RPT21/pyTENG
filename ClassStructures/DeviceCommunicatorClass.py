from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from ClassStructures.RaspberryInterface import RaspberryInterface
from ClassStructures.DaqInterface import *
from PyDAQmx import DAQmxIsTaskDone, bool32
import time

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
        self.AdquisitionTasks = []
        for n, task in enumerate(self.mainWindow.CHANNELS):
            if task["TYPE"] == "analog":
                self.AdquisitionTasks.append(AnalogRead(PLOT_BUFFER=self.mainWindow.plot_buffer,
                                    BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                                    SIGNAL_SELECTOR=None,
                                    BUFFER_SIZE=self.mainWindow.BUFFER_SIZE,
                                    CHANNELS=task["DAQ_CHANNELS"],
                                    SAMPLE_RATE=self.mainWindow.SAMPLE_RATE,
                                    SAMPLES_PER_CALLBACK=self.mainWindow.SAMPLES_PER_CALLBACK,
                                    AdquisitionProgramReference=self.mainWindow,
                                    TRIGGER_SOURCE=task["TRIGGER_SOURCE"]))
            elif task["TYPE"] == "digital":
                self.AdquisitionTasks.append(DigitalRead(PLOT_BUFFER=self.mainWindow.plot_buffer,
                                                        BUFFER_PROCESSOR=self.mainWindow.buffer_processors[n],
                                                        SIGNAL_SELECTOR=None,
                                                        BUFFER_SIZE=self.mainWindow.BUFFER_SIZE,
                                                        CHANNELS=task["DAQ_CHANNELS"],
                                                        SAMPLE_RATE=self.mainWindow.SAMPLE_RATE,
                                                        SAMPLES_PER_CALLBACK=self.mainWindow.SAMPLES_PER_CALLBACK,
                                                        AdquisitionProgramReference=self.mainWindow,
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

        self.mainWindow.moveLinMot[0] = True

        for task in self.AdquisitionTasks:
            task.index = 0
            task.StartTask()

        self.mainWindow.xRecording[0] = True

        if self.mainWindow.automatic_mode:
            self.DO_task_RelayCode.set_lines(self.mainWindow.RESISTANCE_DATA[self.mainWindow.iteration_index]["DAQ_CODE"])
        else:
            self.DO_task_RelayCode.set_lines(self.mainWindow.DAQ_CODE)

        self.DO_task_LinMotTrigger.set_line(1)
        self.mainWindow.start_adquisition_success_signal.emit()

    @pyqtSlot()
    def stop_adquisition(self):

        self.DO_task_LinMotTrigger.set_line(0)
        self.DO_task_PrepareRaspberry.set_line(0)
        self.DO_task_RelayCode.set_lines([0,0,0,0,0,0])

        # Wait until raspberry has saved the LinMot_Enable = 0, then stop the DAQ Adquisition
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

        # After stopping LinMot, we need to register the moment when LinMot_Enable = 0 in the DAQ
        self.mainWindow.moveLinMot[0] = False

        # Wait until all DAQ Tasks stopped (doing an extra callback to store the data)
        all_stopped = False

        done = bool32()
        while not all_stopped:
            all_stopped = True
            for task in self.AdquisitionTasks:
                DAQmxIsTaskDone(task.taskHandle, byref(done))
                if not done.value:
                    all_stopped = False
                    time.sleep(0.1)
                    break
            if all_stopped == True:
                print("All tasks have stopped, saving data ...")

        for n, task in enumerate(self.AdquisitionTasks):
            if task.index != 0:

                data = task.current_buffer[:task.index]

                # In this case this thread will do the saving
                self.mainWindow.buffer_processors[n].save_data(data)

                task.index = 0

            self.raspberry.download_folder(self.rb_remote_path, local_path=self.mainWindow.local_path[0])
            self.raspberry.remove_files_with_extension(self.rb_remote_path)

        if self.mainWindow.automatic_mode:

            # Wait motor return to the origin position and increase iteration_index
            self.mainWindow.update_button_signal.emit()
            self.mainWindow.iteration_index += 1

            if self.mainWindow.iteration_index <= self.mainWindow.iterations:
                print("Waiting LinMot to return to origin position")
                time.sleep(5)

        self.mainWindow.xRecording[0] = False
        self.mainWindow.stop_adquisition_success_signal.emit()