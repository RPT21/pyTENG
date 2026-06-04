import sys
from PyQt5.QtWidgets import QApplication

from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)

from ClassStructures.RLoadSwitch import R_LOAD_SWITCH

# Metadata columns required by the new AcquisitionProgram
METADATA_COLUMNS = {
    "TribuId": {"default": "", "value": "", "type": "str", "limits": None},
    "SampleIdTriboNeg": {"default": "", "value": "", "type": "str", "limits": None},
    "SampleIdTriboPos": {"default": "", "value": "", "type": "str", "limits": None},
    "Date": {"default": None, "value": None, "type": "date", "limits": None},
    "Capacitorld": {"default": "none", "value": "none", "type": "str", "limits": None},
    "RloadId": {"default": "", "value": "", "type": "str", "limits": None},
    "InitialPosition": {"default": -54.0, "value": -54.0, "type": "float", "limits": None},
    "FinalPosition": {"default": -59.4, "value": -59.4, "type": "float", "limits": None},
    "MeasuredParameterMotor": {"default": "", "value": "Pos(mm), F(N), Target Force(N)", "type": "str",
                               "limits": None},
    "ReadingTime (s)": {"default": 0, "value": 0, "type": "int", "limits": [0, None]},
    "Electrode rGO": {"default": False, "value": False, "type": "bool", "limits": None},
    "MotorSpeedDown(m/s)": {"default": 0.5, "value": 0.5, "type": "float", "limits": None},
    "MotorAccelerationDown(m/s)": {"default": 0.5, "value": 0.5, "type": "float", "limits": None},
    "MotorDecelerationDown(m/s)": {"default": 0.5, "value": 0.5, "type": "float", "limits": None},
    "Motor Speed Up(m/s)": {"default": 0.5, "value": 0.5, "type": "float", "limits": None},
    "Motor AccelerationUp(m/s)": {"default": 0.5, "value": 0.5, "type": "float", "limits": None},
    "MotorDecelerationUp(m/s)": {"default": 0.5, "value": 0.5, "type": "float", "limits": None},
    "MotorForceMax": {"default": 0.0, "value": 0.0, "type": "float", "limits": None},
    "Notes": {"default": "", "value": "", "type": "str", "limits": None},
}

R_LOAD_PROFILE = [
    {
        "NAME": "R_LOAD",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS": {
            "Voltage": {"port": "Dev1/ai3", "port_config": DAQmx_Val_Diff, "conversion_source": "none",
                        "conversion_factor": None, "keithley_sense": "none"},
        },

        "TRIGGER_SOURCE": "PFI0",
        # "TRIGGER_SOURCE": None,

        "TYPE": "analog"
    },

    {
        "NAME": "Digital Synchronization",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS": {
            "LinMot_Enable": {"port": "Dev2/port0/line0", "port_config": None, "conversion_source": "none",
                              "conversion_factor": None, "keithley_sense": "none"},
            "LinMot_Up_Down": {"port": "Dev2/port0/line1", "port_config": None, "conversion_source": "none",
                               "conversion_factor": None, "keithley_sense": "none"}
        },

        # "TRIGGER_SOURCE": "PFI0",
        "TRIGGER_SOURCE": None,
        "TYPE": "digital"
    }
]

app = QApplication(sys.argv)

# To debug, use this
debug = False
tribo_lab = True
if debug:
    if tribo_lab:
        exp_dir = r"C:\Users\mmartic\Desktop\RogerTest"
    else:
        exp_dir = r"C:\Users\rpieres\Desktop\Test"
    tribu_id = "PDMSvsNylon"
    rload_id = "R10"
    SampleIdTriboNeg = "PDMS"
    SampleIdTriboPos = "Nylon"
else:
    exp_dir = None
    tribu_id = None
    rload_id = None
    SampleIdTriboNeg = None
    SampleIdTriboPos = None

w = R_LOAD_SWITCH(METADATA_COLUMNS=METADATA_COLUMNS,
               R_LOAD_PROFILE=R_LOAD_PROFILE,
               tribu_id="TribuTest",
               sample_id_neg="SampleNegTest",
               sample_id_pos="SamplePosTest"
               )
w.show()
sys.exit(app.exec_())