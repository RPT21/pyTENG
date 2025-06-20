from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
import numpy as np
from ctypes import c_int32

class DigitalInputTask(Task):
    def __init__(self, line="Dev1/port1/line0"):
        Task.__init__(self)
        self.CreateDIChan(line, "", DAQmx_Val_ChanForAllLines)

    def read_line(self):
        data = np.zeros((1,), dtype=np.uint8)
        read = c_int32()
        self.ReadDigitalLines(1, 10.0, 0, data, 1, read, None, None)
        return data[0]


# Ejemplo de uso
di_task = DigitalInputTask()
di_task.StartTask()

try:
    data = di_task.read_line()
    print(data)
    input("Presiona Enter para salir...")
finally:
    di_task.StopTask()
    di_task.ClearTask()