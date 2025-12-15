from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)

from PyDAQmx import Task, DAQmxIsTaskDone
import numpy as np
from ctypes import byref, c_int32

class DAQTaskBase(Task):
    def __init__(self,
                 PLOT_BUFFER,
                 BUFFER_PROCESSOR,
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
        self.BUFFER_PROCESSOR = BUFFER_PROCESSOR
        self.processor_signal = BUFFER_PROCESSOR.process_buffer_signal
        self.data_column_selector = SIGNAL_SELECTOR

        self.buffer1 = np.empty((self.BUFFER_SIZE, self.number_channels))
        self.buffer2 = np.empty((self.BUFFER_SIZE, self.number_channels))
        self.current_buffer = self.buffer1
        self.index = 0
        self.mainWindow = AdquisitionProgramReference
        self.stop_at_next_callback = False

        if TRIGGER_SOURCE:
            self.CfgDigEdgeStartTrig(TRIGGER_SOURCE, DAQmx_Val_Rising)


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

        # Determine buffer data type
        self.buffer1.astype(np.float64)
        self.buffer2.astype(np.float64)

    def EveryNCallback(self):
        try:
            data = np.empty((self.SAMPLES_PER_CALLBACK, self.number_channels), dtype=np.float64)
            read = c_int32()
            self.ReadAnalogF64(self.SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, data, data.size,
                               byref(read), None)

            if self.mainWindow.moveLinMot[0] or not self.stop_at_next_callback:
                if not self.mainWindow.moveLinMot[0]:
                    self.stop_at_next_callback = True

                if self.mainWindow.actual_plotter is self:
                    self.plot_buffer[self.write_index:self.write_index + self.SAMPLES_PER_CALLBACK] = data[
                        :, self.data_column_selector.value()[-1]]
                    self.write_index = (self.write_index + self.SAMPLES_PER_CALLBACK) % self.plot_buffer.size

                self.current_buffer[self.index:self.index + self.SAMPLES_PER_CALLBACK, :] = data
                self.index += self.SAMPLES_PER_CALLBACK

                if self.index >= self.BUFFER_SIZE:
                    if not self.BUFFER_PROCESSOR.isSaving:
                        full_buffer = self.current_buffer
                        self.current_buffer = self.buffer1 if self.current_buffer is self.buffer2 else self.buffer2
                        self.index = 0
                        self.processor_signal.emit(full_buffer)
                    else:
                        self.mainWindow.automatic_mode = False
                        self.mainWindow.stop_for_error = True
                        self.mainWindow.trigger_adquisition_signal.emit()
                        raise Exception("Fatal error thread race condition reached when saving into disk!")
            else:
                self.StopTask()

        except Exception as e:
            print(f"DAQ error in callback: {e}")

        return 0

class DigitalRead(DAQTaskBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for channel in list(self.CHANNELS.values()):
            self.CreateDIChan(channel[0]["port"],
                              "",
                              DAQmx_Val_ChanForAllLines)

        self.CfgSampClkTiming("", self.SAMPLE_RATE, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.SAMPLES_PER_CALLBACK)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, self.SAMPLES_PER_CALLBACK, 0)

        # Determine buffer data type
        self.buffer1.astype(np.uint32)
        self.buffer2.astype(np.uint32)

    def EveryNCallback(self):
        try:
            data = np.empty((self.SAMPLES_PER_CALLBACK, self.number_channels), dtype=np.uint32)
            read = c_int32()
            self.ReadDigitalU32(self.SAMPLES_PER_CALLBACK, 10.0, DAQmx_Val_GroupByScanNumber, data, data.size,
                               byref(read), None)

            if self.mainWindow.moveLinMot[0] or not self.stop_at_next_callback:
                if not self.mainWindow.moveLinMot[0]:
                    self.stop_at_next_callback = True

                if self.mainWindow.actual_plotter is self:
                    self.plot_buffer[self.write_index:self.write_index + self.SAMPLES_PER_CALLBACK] = data[
                        :, self.data_column_selector.value()[-1]]
                    self.write_index = (self.write_index + self.SAMPLES_PER_CALLBACK) % self.plot_buffer.size

                self.current_buffer[self.index:self.index + self.SAMPLES_PER_CALLBACK, :] = data
                self.index += self.SAMPLES_PER_CALLBACK

                if self.index >= self.BUFFER_SIZE:
                    if not self.BUFFER_PROCESSOR.isSaving:
                        full_buffer = self.current_buffer
                        self.current_buffer = self.buffer1 if self.current_buffer is self.buffer2 else self.buffer2
                        self.index = 0
                        self.processor_signal.emit(full_buffer)
                    else:
                        self.mainWindow.automatic_mode = False
                        self.mainWindow.stop_for_error = True
                        self.mainWindow.trigger_adquisition_signal.emit()
                        raise Exception("Fatal error thread race condition reached when saving into disk!")
            else:
                self.StopTask()

        except Exception as e:
            print(f"DAQ error in callback: {e}")

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