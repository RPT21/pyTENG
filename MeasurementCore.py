from DaqInterface import ReadAnalog, WriteDigital
import numpy as np
import scipy.signal as signal
from PyQt5.QtCore import QTimer
from PyQt5 import Qt
from datetime import datetime
from numpy import zeros
from ctypes import *
import ctypes
import sys

def EveryNEventFunc(Task_number, data):
    print("Hello World!", Task_number)

def DoneEventFunc(Task_number, data):
    print("End of Work!", Task_number)

class MeasurementCore:
    def __init__(self):
        self.xRunning = False
        self.actualList = list()
        self.actualConfiguration = dict()
        self.counter = 0
        self.DaqAnalogRead = ReadAnalog(InChans=["ai0"])
        self.DaqDigitalWrite = WriteDigital(Channels=["port0/line0",
                                                      "port0/line1",
                                                      "port0/line2",
                                                      "port0/line3",
                                                      "port0/line4",
                                                      "port0/line5",
                                                      "port0/line6",
                                                      "port0/line7"])

        ReadAnalog.DoneEvent = DoneEventFunc # Pass by reference
        ReadAnalog.EveryNEvent = EveryNEventFunc # Pass by reference

    def startMeasuring(self, Resistance_list, Recording_Configuration):
        self.xRunning = True
        self.actualList = Resistance_list
        self.actualConfiguration = Recording_Configuration

        # Inicialitzem la primera mesura de la DAQ i deixem que la DAQ gestioni les altres mesures
        # El [1, 1] del final és per afegir el trigger del LinMot i de la Raspberry.
        digital_code = [int(bit) for bit in Resistance_list[0]["DAQ_CODE"]] + [1, 1]
        Signal = np.array(digital_code, dtype=np.uint8)
        print("Signal:", Signal)
        self.DaqDigitalWrite.SetDigitalSignal(Signal)

        # Comencem a medir les dades.
        self.DaqAnalogRead.ReadData()

    def stop(self):
        self.xRunning = False

