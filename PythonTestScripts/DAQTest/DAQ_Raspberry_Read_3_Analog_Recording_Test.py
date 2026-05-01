from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from ctypes import byref, c_int32
import numpy as np

CHANNEL_LINMOT_ENABLE = "Dev1/ai0"
CHANNEL_LINMOT_UP_DOWN = "Dev1/ai1"
CHANNEL_TENG = "Dev1/ai2"

# Parámetros
sample_rate = 1000  # Hz
samples_per_read = 100

task = Task()

# Crear canales ai0, ai1, ai2
task.CreateAIVoltageChan(f"{CHANNEL_LINMOT_ENABLE},{CHANNEL_LINMOT_UP_DOWN},{CHANNEL_TENG}", "", DAQmx_Val_RSE, -10.0, 10.0, DAQmx_Val_Volts, None)

# Configurar muestreo con reloj interno, muestreo continuo
task.CfgSampClkTiming("", sample_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, samples_per_read)

task.StartTask()

try:
    while True:
        read = c_int32()
        # Buffer para 3 canales * samples_per_read muestras
        data = np.zeros((samples_per_read * 3,), dtype=np.float64)

        # Leer samples_per_read muestras por canal
        task.ReadAnalogF64(samples_per_read, 10.0, DAQmx_Val_GroupByScanNumber, data, len(data), byref(read), None)

        # data está intercalado: sample1 canal0, sample1 canal1, sample1 canal2, sample2 canal0, ...
        # Para separar canales:
        ch0 = data[0::3]
        # ch0[ch0 < 2] = 0
        # ch0[ch0 > 2] = 1

        ch1 = data[1::3]
        # ch1[ch1 < 2] = 0
        # ch1[ch1 > 2] = 1

        ch2 = data[2::3]

        print(f"Leídas {read.value} muestras por canal")
        print("LINMOT_ENABLE:", ch0)
        print("LINMOT_UP_DOWN:", ch1)
        print("TENG:", ch2)
except KeyboardInterrupt:
    print("Terminado por usuario")

task.StopTask()
task.ClearTask()
