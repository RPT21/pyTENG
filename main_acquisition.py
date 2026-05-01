import sys
from PyQt5.QtWidgets import QApplication

from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)

from ClassStructures.MeasurementCore import AcquisitionProgram

R_LOAD_PROFILE = [
    {
        "NAME": "R_LOAD",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS":{
            "Voltage": {"port": "Dev1/ai3", "port_config": DAQmx_Val_Diff, "conversion_factor": None},
        },

        # "TRIGGER_SOURCE": "PFI0",
        "TRIGGER_SOURCE": None,

        "TYPE": "analog"
    },

    {
        "NAME": "Digital Synchronization",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS":{
            "LinMot_Enable": {"port":"Dev2/port0/line0", "port_config":None, "conversion_factor": None},
            "LinMot_Up_Down": {"port":"Dev2/port0/line1", "port_config":None, "conversion_factor": None}
        },

        # "TRIGGER_SOURCE": "PFI0",
        "TRIGGER_SOURCE": None,
        "TYPE": "digital"
    }
]

OPEN_CIRCUIT_PROFILE = [
    {
        "NAME": "Open Circuit",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS": {
            "Voltage": {"port": "Dev1/ai3", "port_config": DAQmx_Val_Diff, "conversion_factor": None},
        },

        # "TRIGGER_SOURCE": "PFI0",
        "TRIGGER_SOURCE": None,

        "TYPE": "analog"
    },

    {
        "NAME": "Digital Synchronization",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS": {
            "LinMot_Enable": {"port": "Dev2/port0/line0", "port_config": None, "conversion_factor": None},
            "LinMot_Up_Down": {"port": "Dev2/port0/line1", "port_config": None, "conversion_factor": None}
        },

        # "TRIGGER_SOURCE": "PFI0",
        "TRIGGER_SOURCE": None,
        "TYPE": "digital"
    }
]

SHORT_CIRCUIT_CURRENT_PROFILE = [
    {
        "NAME": "Short Circuit",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS": {
            "Current": {"port": "Dev1/ai2", "port_config": DAQmx_Val_RSE, "conversion_factor": 1},
        },

        # "TRIGGER_SOURCE": "PFI0",
        "TRIGGER_SOURCE": None,

        "TYPE": "analog"
    },

    {
        "NAME": "Digital Synchronization",
        "SAMPLE_RATE": 10000,

        "DAQ_CHANNELS": {
            "LinMot_Enable": {"port": "Dev2/port0/line0", "port_config": None, "conversion_factor": None},
            "LinMot_Up_Down": {"port": "Dev2/port0/line1", "port_config": None, "conversion_factor": None}
        },

        # "TRIGGER_SOURCE": "PFI0",
        "TRIGGER_SOURCE": None,
        "TYPE": "digital"
    }
]

# Build DAQ_PROFILES mapping (Default + VR, VOC, ISC copies)
DAQ_PROFILES = {
    "VR": R_LOAD_PROFILE,
    "VOC": OPEN_CIRCUIT_PROFILE,
    "ISC": SHORT_CIRCUIT_CURRENT_PROFILE,
}

METADATA_COLUMNS = {
    "TribuId": {"default": "Nylon6-PDMS", "type": "str", "limits": None},
    "Keithley Used": {"default": False, "type": "bool", "limits": None},
    "Date": {"default": None, "type": "date", "limits": None},
    "Capacitorld": {"default": "none", "type": "str", "limits": None},
    "RloadId": {"default": "R100", "type": "str", "limits": None},
    "InitialPosition": {"default": -54.0, "type": "float", "limits": None},
    "FinalPosition": {"default": -59.4, "type": "float", "limits": None},
    "MeasuredParameterMotor": {"default": "Pos(mm), F(N), Target Force(N)", "type": "str", "limits": None},
    "ReadingTime (s)": {"default": 0, "type": "int", "limits": [0, None]},
    "Electrode rGO": {"default": False, "type": "bool", "limits": None},
    "MotorSpeedDown(m/s)": {"default": 0.5, "type": "float", "limits": None},
    "MotorAccelerationDown(m/s)": {"default": 0.5, "type": "float", "limits": None},
    "MotorDecelerationDown(m/s)": {"default": 0.5, "type": "float", "limits": None},
    "Motor Speed Up(m/s)": {"default": 0.5, "type": "float", "limits": None},
    "Motor AccelerationUp(m/s)": {"default": 0.5, "type": "float", "limits": None},
    "MotorDecelerationUp(m/s)": {"default": 0.5, "type": "float", "limits": None},
    "MotorForceMax": {"default": 0.0, "type": "float", "limits": None},
    "Notes": {"default": "", "type": "str", "limits": None},
}

resistance_list = [{'VALUE': 5,
                  'ATENUATION': 1.0,
                  'DAQ_CODE': [0, 0, 0, 0, 0, 1],
                  'RLOAD_ID': 'Resistance 0'},
                 {'VALUE': 25,
                  'ATENUATION': 1.8,
                  'DAQ_CODE': [0, 0, 1, 0, 0, 1],
                  'RLOAD_ID': 'Resistance 4'},
                 {'VALUE': 35,
                  'ATENUATION': 2.2,
                  'DAQ_CODE': [0, 1, 1, 0, 0, 1],
                  'RLOAD_ID': 'Resistance 6'}]

app = QApplication(sys.argv)

# To debug, use this
debug = True
tribo_lab = True
if debug:
    if tribo_lab:
        exp_dir = r"C:\Users\marre\Documents\TENG_Project_SaveFolder"
    else:
        exp_dir = r"C:\Users\rpieres\Desktop\Test"
    tribu_id = "PDMSvsNylon"
    rload_id = "10"
else:
    exp_dir = None
    tribu_id = None
    rload_id = None

window = AcquisitionProgram(DAQ_PROFILES=DAQ_PROFILES,
                            METADATA_COLUMNS=METADATA_COLUMNS,
                            automatic_mode=False,
                            RESISTANCE_DATA=resistance_list,
                            measure_time=1,
                            exp_dir=exp_dir,
                            tribu_id=tribu_id,
                            rload_id=rload_id)
window.show()
sys.exit(app.exec_())
