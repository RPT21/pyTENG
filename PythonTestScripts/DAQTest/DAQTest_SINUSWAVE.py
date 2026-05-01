import numpy as np
from PyDAQmx import Task
import PyDAQmx.DAQmxFunctions as daq
import PyDAQmx.DAQmxConstants as const

if __name__ == "__main__":
    
    # Parámetros de la señal
    fs = 1000  # Frecuencia de muestreo
    f = 10  # Frecuencia de la onda seno
    t = np.arange(0, 5, 1 / fs)
    sine_wave = 2 * np.sin(2 * np.pi * f * t)  # Amplitud de 2 V

    task = Task()
    task.CreateAOVoltageChan("Dev1/ao2", "", -10.0, 10.0, const.DAQmx_Val_Volts, None)
    task.CfgSampClkTiming("", fs, const.DAQmx_Val_Rising, const.DAQmx_Val_FiniteSamps, len(sine_wave))
    task.WriteAnalogF64(len(sine_wave), False, 10.0, const.DAQmx_Val_GroupByChannel, sine_wave, None, None)
    task.StartTask()
    task.WaitUntilTaskDone(10.0)
    task.StopTask()
    task.ClearTask()
