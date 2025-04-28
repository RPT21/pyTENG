#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 14:12:43 2019

@author: aguimera
"""

import PyDAQmx as Daq
import sys
import ctypes
from ctypes import byref, c_int32
import numpy as np


class Buffer2D(np.ndarray):
    def __new__(subtype, BufferSize, nChannels,
                dtype=float, buffer=None, offset=0,
                strides=None, order=None, info=None):
        # Create the ndarray instance of our type, given the usual
        # ndarray input arguments.  This will call the standard
        # ndarray constructor, but return an object of our type.
        # It also triggers a call to InfoArray.__array_finalize__
        shape = (BufferSize, nChannels)
        obj = super(Buffer2D, subtype).__new__(subtype, shape, dtype,
                                               buffer, offset, strides,
                                               order)
        # set the new 'info' attribute to the value passed
        obj.counter = 0
        obj.totalind = 0
        # Finally, we must return the newly created object:
        return obj

    def __array_finalize__(self, obj):
        # see InfoArray.__array_finalize__ for comments
        if obj is None:
            return
        self.bufferind = getattr(obj, 'bufferind', None)

    def AddData(self, NewData):
        newsize = NewData.shape[0]
        if newsize > self.shape[0]:
            self[:, :] = NewData[:self.shape[0], :]
        else:
            self[0:-newsize, :] = self[newsize:, :]
            self[-newsize:, :] = NewData
        self.counter += newsize
        self.totalind += newsize

    def IsFilled(self):
        return self.counter >= self.shape[0]

    def Reset(self):
        self.counter = 0


def GetDevName():
    # Get Device Name of Daq Card
    n = 1024
    buff = ctypes.create_string_buffer(n)
    Daq.DAQmxGetSysDevNames(buff, n)
    if sys.version_info >= (3,):
        value = buff.value.decode()
    else:
        value = buff.value

    Dev = None
    value = value.replace(' ', '')
    for dev in value.split(','):
        if dev.startswith('Sim'):
            continue
        Dev = dev + '/{}'

    if Dev is None:
        print('ERRROORR dev not found ', value)

    return Dev

##############################################################################


class DaqTaskBase(Daq.Task):
    def __del__(self):
        pass
        #print('Delete Task : ', self.taskHandle)
        # # self.StopTask()
        # # self.UnregisterEveryNSamplesEvent()
        # # self.UnregisterDoneEvent()
        # self.ClearTask()


class ReadAnalog(DaqTaskBase):
    EveryNEvent = None
    DoneEvent = None

    def __init__(self, InChans, Range=5.0, Diff=False):
        Daq.Task.__init__(self)
        self.Channels = InChans

        Dev = GetDevName()
        for Ch in self.Channels:
            if Diff is False:
                self.CreateAIVoltageChan(Dev.format(Ch), "",
                                         Daq.DAQmx_Val_RSE,
                                         -Range, Range,
                                         Daq.DAQmx_Val_Volts, None)
            if Diff is True:
                self.CreateAIVoltageChan(Dev.format(Ch), "",
                                         Daq.DAQmx_Val_Diff,
                                         -Range, Range,
                                         Daq.DAQmx_Val_Volts, None)
        self.AutoRegisterDoneEvent(0)
        # print('INIT Analog Inputs : ', self.taskHandle)
        # print(self.Channels)

    def ReadData(self, Fs=1000, nSamps=10000, EverySamps=1000):
        self.Fs = Fs
        self.EverySamps = EverySamps
        self.Data = Buffer2D(BufferSize=nSamps, nChannels=len(self.Channels))

        self.CfgSampClkTiming("", Fs, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_FiniteSamps, nSamps)

        self.AutoRegisterEveryNSamplesEvent(Daq.DAQmx_Val_Acquired_Into_Buffer,
                                            self.EverySamps, 0)
        self.StartTask()

    def ReadContData(self, Fs, EverySamps, **kwargs):
        self.Fs = Fs
        self.EverySamps = np.int32(EverySamps)
        self.Data = None

        self.CfgSampClkTiming("", Fs, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_ContSamps,
                              self.EverySamps)

        self.CfgInputBuffer(self.EverySamps*10)
        self.AutoRegisterEveryNSamplesEvent(Daq.DAQmx_Val_Acquired_Into_Buffer,
                                            self.EverySamps, 0)

        self.StartTask()

    def StopContData(self):
        self.StopTask()

    def EveryNCallback(self):
        # print('EveryN')
        read = c_int32()
        data = np.zeros((self.EverySamps, len(self.Channels)))
        self.ReadAnalogF64(self.EverySamps, 10.0,
                           Daq.DAQmx_Val_GroupByScanNumber,
                           data, data.size, byref(read), None)

        if self.Data is not None:
            self.Data.AddData(data)

        if self.EveryNEvent:
            self.EveryNEvent(data)

    def DoneCallback(self, status):
        # print('Done')
        self.StopTask()
        self.UnregisterEveryNSamplesEvent()
        if self.DoneEvent:
            self.DoneEvent(self.Data)
        return 0  # The function should return an integer

##############################################################################


class WriteAnalog(DaqTaskBase):

    '''
    Class to write data to Daq card
    '''

    def __init__(self, Channels):
        Daq.Task.__init__(self)
        Dev = GetDevName()
        for Ch in Channels:
            self.CreateAOVoltageChan(Dev.format(Ch), "",
                                     -5.0, 5.0, Daq.DAQmx_Val_Volts, None)
        self.DisableStartTrig()
        self.StopTask()
        # print('INIT Analog OutPuts : ', self.taskHandle)
        # print(Channels)

    def SetVal(self, value):
        self.StartTask()
        self.WriteAnalogScalarF64(1, -1, value, None)
        self.StopTask()

    def SetSignal(self, Signal, nSamps, FsBase='ai/SampleClock', FsDiv=1):
        read = c_int32()

        self.CfgSampClkTiming(FsBase, FsDiv, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_FiniteSamps, nSamps)

        self.CfgDigEdgeStartTrig('ai/StartTrigger', Daq.DAQmx_Val_Rising)
        self.WriteAnalogF64(nSamps, False, -1, Daq.DAQmx_Val_GroupByChannel,
                            Signal, byref(read), None)
        self.StartTask()

    def SetContSignal(self, Signal, nSamps, FsBase='ai/SampleClock', FsDiv=1):
        read = c_int32()

        self.CfgSampClkTiming(FsBase, FsDiv, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_ContSamps, nSamps)

        self.CfgDigEdgeStartTrig('ai/StartTrigger', Daq.DAQmx_Val_Rising)
        self.WriteAnalogF64(nSamps, False, -1, Daq.DAQmx_Val_GroupByChannel,
                            Signal, byref(read), None)
        self.StartTask()


##############################################################################


class WriteDigital(DaqTaskBase):

    '''
    Class to write data to Daq card
    '''

    def __init__(self, Channels):
        Daq.Task.__init__(self)
        Dev = GetDevName()
        for Ch in Channels:
            self.CreateDOChan(Dev.format(Ch), "",
                              Daq.DAQmx_Val_ChanForAllLines)

        self.DisableStartTrig()
        self.StopTask()
        # print('INIT Digital OutPuts : ', self.taskHandle)
        # print(Channels)

    def SetDigitalSignal(self, Signal):
        Sig = Signal.astype(np.uint8)
        self.WriteDigitalLines(1, 1, 10.0, Daq.DAQmx_Val_GroupByChannel,
                               Sig, None, None)

    def SetContSignal(self, Signal):
        read = c_int32()
        self.CfgSampClkTiming('ai/SampleClock', 1, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_ContSamps, Signal.shape[1])
        self.CfgDigEdgeStartTrig('ai/StartTrigger', Daq.DAQmx_Val_Rising)
        self.WriteDigitalLines(Signal.shape[1], False, 1,
                               Daq.DAQmx_Val_GroupByChannel,
                               Signal, byref(read), None)
        self.StartTask()
#        print('End SetSingal', read)

##############################################################################





