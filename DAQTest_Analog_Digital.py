from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from numpy import zeros
import numpy as np
import time

class DataAcquisitionTask(Task):
    def __init__(self):
        Task.__init__(self)
        self.data = zeros(1000)
        self.a = []
        self.CreateAIVoltageChan("Dev1/ai0", "", DAQmx_Val_RSE, -10.0, 10.0, DAQmx_Val_Volts, None)
        self.CfgSampClkTiming("", 10000.0, DAQmx_Val_Rising, DAQmx_Val_ContSamps, 1000)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, 1000, 0)
        self.AutoRegisterDoneEvent(0)

    def EveryNCallback(self):
        read = int32()
        self.ReadAnalogF64(1000, 10.0, DAQmx_Val_GroupByScanNumber, self.data, 1000, byref(read), None)
        self.a.extend(self.data.tolist())
        print(self.data[0])  # Simplemente muestra el primer dato
        return 0

    def DoneCallback(self, status):
        print("Status", status.value)
        return 0


class DigitalOutputTask(Task):
    def __init__(self, line="Dev1/port0/line0"):
        Task.__init__(self)
        self.CreateDOChan(line, "", DAQmx_Val_ChanForAllLines)

    def set_line(self, value):
        """value = 0 (OFF) o 1 (ON)"""
        data = np.array([value], dtype=np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, DAQmx_Val_GroupByChannel, data, None, None)


# Ejecución principal
if __name__ == "__main__":
    ai_task = DataAcquisitionTask()
    do_task = DigitalOutputTask()

    ai_task.StartTask()

    try:
        for i in range(5):  # Adquirimos datos durante 5 segundos
            time.sleep(1)
            if i % 2 == 0:
                do_task.set_line(1)  # Encender cada 2 segundos
                print("Pin digital: ON")
            else:
                do_task.set_line(0)  # Apagar
                print("Pin digital: OFF")
    finally:
        ai_task.StopTask()
        ai_task.ClearTask()
        do_task.ClearTask()

    print(f"Total muestras adquiridas: {len(ai_task.a)}")
