from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
import numpy as np

class DigitalOutputTask(Task):
    def __init__(self):
        Task.__init__(self)
        # Configuramos las 8 líneas del puerto 0
        self.CreateDOChan("Dev1/port0/line0:7", "", DAQmx_Val_ChanForAllLines)

    def set_lines(self, values):
        """values debe ser una lista o array de 8 valores (0 o 1)"""
        data = np.array(values, dtype=np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, DAQmx_Val_GroupByChannel, data, None, None)

# Ejemplo de uso
do_task = DigitalOutputTask()
do_task.StartTask()

try:
    do_task.set_lines([0, 0, 0, 0, 0, 0, 0, 1])  # Encenem les linies
    input("Presiona Enter para salir...")
    do_task.set_lines([0, 0, 0, 0, 0, 0, 0, 0])  # Apaguem les linies (necessari si no queda encès)
finally:
    do_task.StopTask()
    do_task.ClearTask()

