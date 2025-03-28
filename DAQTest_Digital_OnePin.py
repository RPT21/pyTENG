from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
import numpy as np

class DigitalOutputTask(Task):
    def __init__(self, line="Dev1/port0/line0"):
        Task.__init__(self)
        self.CreateDOChan(line, "", DAQmx_Val_ChanForAllLines)

    def set_line(self, value):
        """value = 0 (OFF) o 1 (ON)"""
        print("Line set to", value)
        data = np.array([value], dtype=np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, DAQmx_Val_GroupByChannel, data, None, None)

# Ejemplo de uso
do_task = DigitalOutputTask()
do_task.StartTask()

try:
    do_task.set_line(1)  # Encendemos la linea
    input("Presiona Enter para salir...")
    do_task.set_line(0)
finally:
    do_task.StopTask()
    do_task.ClearTask()