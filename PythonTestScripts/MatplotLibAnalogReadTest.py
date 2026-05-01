import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *
from ctypes import byref
import threading
import time

# Configuración del buffer compartido
BUFFER_SIZE = 1000
CHUNK_SIZE = 100
plot_data = np.zeros(BUFFER_SIZE)
plot_lock = threading.Lock()

# Tarea DAQ con callback EveryN
class DAQTask(Task):
    def __init__(self, sample_rate=1000, samples_per_chunk=CHUNK_SIZE):
        super().__init__()
        self.buffer = np.zeros(samples_per_chunk, dtype=np.float64)
        self.samples_per_chunk = samples_per_chunk

        self.CreateAIVoltageChan("Dev1/ai0", "", DAQmx_Val_Cfg_Default, -10.0, 10.0,
                                 DAQmx_Val_Volts, None)
        self.CfgSampClkTiming("", sample_rate, DAQmx_Val_Rising,
                              DAQmx_Val_ContSamps, samples_per_chunk)

        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer,
                                            samples_per_chunk, 0)

    def Start(self):
        self.StartTask()

    def Stop(self):
        self.StopTask()
        self.ClearTask()

    # Callback que se llama cada N muestras
    def EveryNCallback(self):
        read = int32()
        try:
            self.ReadAnalogF64(self.samples_per_chunk, 10.0, DAQmx_Val_GroupByChannel,
                               self.buffer, self.samples_per_chunk, byref(read), None)

            with plot_lock:
                global plot_data
                plot_data = np.roll(plot_data, -self.samples_per_chunk)
                plot_data[-self.samples_per_chunk:] = self.buffer

        except Exception as e:
            print("Error en callback:", e)
        return 0

# Configurar matplotlib
fig, ax = plt.subplots()
line, = ax.plot(plot_data)
ax.set_ylim(-10, 10)
ax.set_title("DAQ Analog Input - EveryNCallback + Matplotlib")
ax.set_xlabel("Muestras")
ax.set_ylabel("Voltaje (V)")

# Función de actualización del gráfico
def update_plot(frame):
    with plot_lock:
        line.set_ydata(plot_data.copy())
    return line,

# Inicializar DAQ
daq = DAQTask(sample_rate=1000, samples_per_chunk=CHUNK_SIZE)
daq.Start()

# Iniciar animación
ani = FuncAnimation(fig, update_plot, interval=100, blit=True, cache_frame_data=False)

try:
    plt.show()
    time.sleep(5)
finally:
    daq.Stop()

