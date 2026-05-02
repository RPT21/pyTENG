from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines, DAQmx_Val_ChanPerLine)

from PyDAQmx import Task, DAQmxIsTaskDone
import numpy as np
from ctypes import byref, c_int32

class DAQTaskBase(Task):
    def __init__(self,
                 TASK,
                 BUFFER_PROCESSOR,
                 DAQ_USB_TRANSFER_FREQUENCY,
                 BUFFER_SAVING_TIME_INTERVAL,
                 TimeWindowLength,
                 AcquisitionProgramReference):

        super().__init__()

        self.NAME = TASK["NAME"]
        self.CHANNELS = TASK["DAQ_CHANNELS"]
        self.SAMPLE_RATE = TASK["SAMPLE_RATE"]
        self.TRIGGER_SOURCE = TASK["TRIGGER_SOURCE"]
        self.number_channels = len(self.CHANNELS)

        # The order of definition is the order of saving into buffer, so we introduce an index to know the position:
        for idx, (name, config) in enumerate(TASK["DAQ_CHANNELS"].items()):
            TASK["DAQ_CHANNELS"][name] = [config, idx]

        # Introduce the DAQ Task reference into the TASK definition for later use in the acquisition graph
        TASK["DAQ_TASK_REFERENCE"] = self

        # Get internal DAQ buffer size based on total sampling rate
        internal_buffer_size = self._get_daq_internal_buffer_size(self.SAMPLE_RATE)

        # Calculate initial SAMPLES_PER_CALLBACK
        initial_samples_per_callback = int(self.SAMPLE_RATE/ DAQ_USB_TRANSFER_FREQUENCY)

        # Find divisors of internal buffer size
        divisors_of_internal_buffer = self._find_divisors(internal_buffer_size)

        # Pick the divisor closest to initial_samples_per_callback
        samples_per_callback = min(divisors_of_internal_buffer,
                                   key=lambda x: abs(x - initial_samples_per_callback))

        # Log the adjustment if it changed
        if samples_per_callback != initial_samples_per_callback:
            print(
                f"Task {self.NAME}: Adjusted SAMPLES_PER_CALLBACK from {initial_samples_per_callback} to {samples_per_callback}")
            print(f"  Task sampling rate: {self.SAMPLE_RATE} Hz, DAQ Internal buffer size: {internal_buffer_size}")

        # Calculate other parameters
        callbacks_per_buffer = int(BUFFER_SAVING_TIME_INTERVAL * DAQ_USB_TRANSFER_FREQUENCY)
        plot_buffer_size = ((self.SAMPLE_RATE * TimeWindowLength) // samples_per_callback) * samples_per_callback

        self.BUFFER_SIZE = samples_per_callback * callbacks_per_buffer
        self.PLOT_BUFFER_SIZE = plot_buffer_size
        self.SAMPLES_PER_CALLBACK = samples_per_callback
        self.INTERNAL_BUFFER_SIZE = internal_buffer_size

        # Define the plot buffer
        self.plot_buffer = np.empty((self.PLOT_BUFFER_SIZE, self.number_channels), dtype=np.float64)
        self.plot_buffer.fill(np.nan)
        self.write_index = 0

        # Define the Buffer Processor Save Signal
        self.BUFFER_PROCESSOR = BUFFER_PROCESSOR
        self.processor_signal = BUFFER_PROCESSOR.process_buffer_signal

        # Define the two buffer switching architecture
        self.buffer1 = np.empty((self.BUFFER_SIZE, self.number_channels), dtype=np.float64)
        self.buffer2 = np.empty((self.BUFFER_SIZE, self.number_channels), dtype=np.float64)
        self.current_buffer = self.buffer1
        self.index = 0

        # Connect with the main window
        self.mainWindow = AcquisitionProgramReference

        # Apply conversion factors only when at least one of the factors is not None
        conv_factors = [ch[0]["conversion_factor"] for ch in self.CHANNELS.values()]
        self.xApplyFactors = any(v is not None for v in conv_factors)

        if self.TRIGGER_SOURCE:
            self.CfgDigEdgeStartTrig(self.TRIGGER_SOURCE, DAQmx_Val_Rising)

    def _get_daq_internal_buffer_size(self, task_sampling_rate):
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

    def _find_divisors(self, n):
        """Find all divisors of n, sorted"""
        divisors = set()
        for i in range(1, int(np.sqrt(n)) + 1):
            if n % i == 0:
                divisors.add(i)
                divisors.add(n // i)
        return sorted(divisors)


class AnalogRead(DAQTaskBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for channel in list(self.CHANNELS.values()):
            self.CreateAIVoltageChan(channel[0]["port"],
                                     "",
                                     channel[0]["port_config"],
                                     -10.0,
                                     10.0,
                                     DAQmx_Val_Volts,
                                     None)

        self.CfgSampClkTiming("", self.SAMPLE_RATE, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.SAMPLES_PER_CALLBACK)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, self.SAMPLES_PER_CALLBACK, 0)

        # Conversion factor vector:
        self.conv_factors = np.array([
            channel[0]["conversion_factor"] if channel[0]["conversion_factor"] is not None else 1
            for channel in list(self.CHANNELS.values())
        ], dtype=np.float64)

        # Determine buffer data type
        self.data = np.empty((self.SAMPLES_PER_CALLBACK, self.number_channels), dtype=np.float64)

        # Set the type of task
        self.task_type = "analog"

    def EveryNCallback(self):
        try:
            samples_read = c_int32()
            self.ReadAnalogF64(self.SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, self.data, self.data.size,
                               byref(samples_read), None)

            if not self.mainWindow.xRecording[0]:
                return

            if self.mainWindow.moveLinMot[0]:

                # Multiply by the conversion_factor if necessary (using in-place multiplication):
                if self.xApplyFactors:
                    self.data *= self.conv_factors

                # Store data in the plot buffer
                self.plot_buffer[self.write_index:self.write_index + self.SAMPLES_PER_CALLBACK, :] = self.data
                self.write_index = (self.write_index + self.SAMPLES_PER_CALLBACK) % self.PLOT_BUFFER_SIZE

                # Store data in the save buffer
                self.current_buffer[self.index:self.index + self.SAMPLES_PER_CALLBACK, :] = self.data
                self.index += self.SAMPLES_PER_CALLBACK

                if self.index >= self.BUFFER_SIZE:
                    if not self.BUFFER_PROCESSOR.isSaving:
                        full_buffer = self.current_buffer
                        self.current_buffer = self.buffer1 if self.current_buffer is self.buffer2 else self.buffer2
                        self.index = 0
                        self.processor_signal.emit(full_buffer)
                    else:
                        if not self.mainWindow.error_flag:
                            self.mainWindow.automatic_mode = False
                            self.mainWindow.error_flag = True
                            self.mainWindow.trigger_acquisition_signal.emit()
                            print("\033[91mFatal error thread race condition reached when saving into disk!\033[0m")
            else:
                self.StopTask()

        except Exception as e:
            if not self.mainWindow.error_flag:
                print(f"Analog DAQ error in callback: {e}")
                self.mainWindow.automatic_mode = False
                self.mainWindow.error_flag = True
                self.mainWindow.trigger_acquisition_signal.emit()
                print("\033[91mAcquisition has stopped due to a DAQ acquisition error\033[0m")

        return 0

class DigitalRead(DAQTaskBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Save the line index for each channel
        lines_index = list()

        # Create a channel for each line
        for channel in list(self.CHANNELS.values()):

            # Configuration:
                # DAQmx_Val_ChanForAllLines (uses a UINT32 to read all the port)
                # DAQmx_Val_ChanPerLine (uses a UINT32 for each line you are reading)

            # Each time you call CreateDIChan, it creates a channel. We have two operating modes:
            # DAQmx_Val_ChanForAllLines and DAQmx_Val_ChanPerLine. In the first case, each channel returns a sample.
            # This sample contains the information of all the lines of the port (the specified lines must be on the same port).
            # On the other hand, if we use DAQmx_Val_ChanPerLine, it returns a sample for each line defined in that channel.
            # IMPORTANT: Each sample is always a UINT32, and the bit is located in the position of the chosen line;
            # for example, DI2 is written in bit 2 of the UINT32.

            self.CreateDIChan(channel[0]["port"],
                              "",
                            DAQmx_Val_ChanForAllLines)
            lines_index.append(int(channel[0]["port"][-1]))

        # Define the task parameters
        self.CfgSampClkTiming("", self.SAMPLE_RATE, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.SAMPLES_PER_CALLBACK)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, self.SAMPLES_PER_CALLBACK, 0)

        # Define the line shifts:
        self.shifts = np.array(lines_index, dtype=np.uint32)

        # Conversion factor vector:
        self.conv_factors = np.array([
            channel[0]["conversion_factor"] if channel[0]["conversion_factor"] is not None else 1
            for channel in list(self.CHANNELS.values())
        ], dtype=np.uint32)

        # Determine buffer data type
        self.data = np.empty((self.SAMPLES_PER_CALLBACK, self.number_channels), dtype=np.uint32)

        # Set the type of task
        self.task_type = "digital"

    def EveryNCallback(self):
        try:
            samples_read = c_int32()
            self.ReadDigitalU32(self.SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, self.data, self.data.size,
                               byref(samples_read), None)

            if not self.mainWindow.xRecording[0]:
                return

            if self.mainWindow.moveLinMot[0]:

                # Right-Shift correction (assuming 1 line per channel) and doing it in-place
                self.data >>= self.shifts

                # Multiply by the conversion_factor if necessary (using in-place multiplication):
                if self.xApplyFactors:
                    self.data *= self.conv_factors

                self.plot_buffer[self.write_index:self.write_index + self.SAMPLES_PER_CALLBACK, :] = self.data
                self.write_index = (self.write_index + self.SAMPLES_PER_CALLBACK) % self.PLOT_BUFFER_SIZE

                self.current_buffer[self.index:self.index + self.SAMPLES_PER_CALLBACK, :] = self.data
                self.index += self.SAMPLES_PER_CALLBACK

                if self.index >= self.BUFFER_SIZE:
                    if not self.BUFFER_PROCESSOR.isSaving:
                        full_buffer = self.current_buffer
                        self.current_buffer = self.buffer1 if self.current_buffer is self.buffer2 else self.buffer2
                        self.index = 0
                        self.processor_signal.emit(full_buffer)
                    else:
                        if not self.mainWindow.error_flag:
                            self.mainWindow.automatic_mode = False
                            self.mainWindow.error_flag = True
                            self.mainWindow.trigger_acquisition_signal.emit()
                            print("\033[91mFatal error thread race condition reached when saving into disk!\033[0m")
            else:
                self.StopTask()

        except Exception as e:
            if not self.mainWindow.error_flag:
                print(f"Digital DAQ error in callback: {e}")
                self.mainWindow.automatic_mode = False
                self.mainWindow.error_flag = True
                self.mainWindow.trigger_acquisition_signal.emit()
                print("\033[91mAcquisition has stopped due to a DAQ acquisition error\033[0m")

        return 0

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