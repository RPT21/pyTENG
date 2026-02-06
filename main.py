# Importing PyQt(5 or 6 version) from qtpy (compatibility abstraction layer for different PyQt versions)
# PyQt5 is an adapted version of C/C++ Qt framework for python to do GUI applications
from qtpy import QtWidgets
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFileDialog, QPushButton, QDesktopWidget

# Importing pyqtgraph (module of C/C++ Qt framework) to do ParameterTree widgets and plotting
from pyqtgraph.parametertree import ParameterTree

# Accessing python interpreter variables and functions
import sys

# Importing custom classes and functions
from ReadExcel import read_excel
from TreeStructures.ResistancePanel import ResistancePanel
from TreeStructures.LinMotControl import LinMotControl
from TreeStructures.RecordingParameters import RecordingParameters
from MeasurementCore import AcquisitionProgram
from ClassStructures.DaqInterface import DigitalOutputTask_MultipleChannels, DigitalOutputTask

from PyDAQmx.DAQmxConstants import (DAQmx_Val_RSE, DAQmx_Val_Volts, DAQmx_Val_Diff,
                                    DAQmx_Val_Rising, DAQmx_Val_ContSamps,
                                    DAQmx_Val_GroupByScanNumber, DAQmx_Val_Acquired_Into_Buffer,
                                    DAQmx_Val_GroupByChannel, DAQmx_Val_ChanForAllLines)

# Function to convert a Parameter into a dict
def parameter_to_dict(param):
    result = {}
    for child in param.children():
        if child.children():
            # If it has more children inside, do recursive calls
            result[child.name()] = parameter_to_dict(child)
        else:
            result[child.name()] = child.value()
    return result


def set_group_readonly(group, readonly=True):
    group.setReadonly(readonly)
    for child in group.children():
        if child.hasChildren():
            set_group_readonly(child, readonly)
        else:
            child.setReadonly(readonly)


class MainWindow(QWidget):
    ''' Main Window '''

    def __init__(self, RelayCodeLines="Dev1/port0/line0:5", LinMotTriggerLine="Dev1/port0/line7"):
        super(MainWindow, self).__init__()
        self.layout = QVBoxLayout(self)

        self.resize(500, 1000)  # width x height
        self.center()  # Call the center function

        self.setWindowTitle('TENG Control Software')

        # Add objects to main window

        # start Button
        self.btnAcq = QPushButton("Start Measure")
        self.layout.addWidget(self.btnAcq)

        # load Button
        self.btnLoad = QPushButton("Load Parameters")
        self.layout.addWidget(self.btnLoad)

        # Connect the button to a method
        self.btnAcq.clicked.connect(self.on_btnStart)
        self.btnLoad.clicked.connect(self.on_loadParameters)

        self.groupBox_ControlPanel = QGroupBox("Control Panel")
        self.blockLayout_ControlPanel = QVBoxLayout()
        self.groupBox_ControlPanel.setLayout(self.blockLayout_ControlPanel)

        # Connect to DAQ:
        self.RelayCodeLines = RelayCodeLines
        self.LinMotTriggerLine = LinMotTriggerLine
        self.DO_task_RelayCode = DigitalOutputTask_MultipleChannels(channels=self.RelayCodeLines)
        self.DO_task_LinMotTrigger = DigitalOutputTask(line=self.LinMotTriggerLine)

        # Definim el ParameterTree
        self.ParameterTree_ControlPanel = ParameterTree()

        # Definim el ParameterGroup ResistancePanel
        self.ResistancePanel = ResistancePanel(DO_task_RelayCode=self.DO_task_RelayCode,
                                               dictionary_parameters=None,
                                               name='Resistance Panel',
                                               title='Resistance Panel')

        # Definim el ParameterGroup LinMotControl
        self.LinMotControl = LinMotControl(DO_task_LinMotTrigger=self.DO_task_LinMotTrigger,
                                           name='LinMot Control',
                                           title='LinMot Control')

        # Definim el ParameterGroup RecordingParameters
        self.RecordingParameters = RecordingParameters(name='Recording Parameters',
                                                       title='Recording Parameters')

        # Afegim els ParameterGroups
        self.ParameterTree_ControlPanel.setParameters(self.ResistancePanel)
        self.ParameterTree_ControlPanel.addParameters(self.LinMotControl)
        self.ParameterTree_ControlPanel.addParameters(self.RecordingParameters)

        # Configurem el ParameterTree
        self.ParameterTree_ControlPanel.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.ParameterTree_ControlPanel.setColumnWidth(0, 220)

        # Afegim el ParameterTree al layout del GroupBox
        self.blockLayout_ControlPanel.addWidget(self.ParameterTree_ControlPanel)

        # Afegim el GroupBox al layout de la GUI
        self.layout.addWidget(self.groupBox_ControlPanel)

        # The order of definition is the order of saving into buffer so we need to put the order in the list
        self.CHANNELS = [
        {
            "NAME":"Dev1",

            "DAQ_CHANNELS":{
                "Voltage": [{"port":"Dev1/ai2", "port_config":DAQmx_Val_Diff}, 0],
                "Current": [{"port":"Dev1/ai3", "port_config":DAQmx_Val_RSE}, 1],
            },

            "TRIGGER_SOURCE":"PFI0"
            # "TRIGGER_SOURCE":None
        },

        {
            "NAME":"Dev2",

            "DAQ_CHANNELS":{
                "LinMot_Enable": [{"port":"Dev2/ai0", "port_config":DAQmx_Val_RSE}, 0],
                "LinMot_Up_Down": [{"port":"Dev2/ai1", "port_config":DAQmx_Val_RSE}, 1]
            },

            "TRIGGER_SOURCE":"PFI0"
            # "TRIGGER_SOURCE":None
        }
    ]

        self.AcquisitionProgram = None
        self.mainWindowButtons = {"btnAcq":self.btnAcq,
                                  "btnLoad":self.btnLoad}
        self.mainWindowParamGroups = {"ResistancePanel":self.ResistancePanel,
                                      "LinMotControl":self.LinMotControl,
                                      "RecordingParameters":self.RecordingParameters}

        # Activate sigValueChanged events after initialization
        self.ResistancePanel.ManualTriggering.initialized_success()
        self.LinMotControl.initialized_success()

    def center(self):
        # Get the screen geometry
        screen_rect = QDesktopWidget().availableGeometry()
        screen_center = screen_rect.center()

        # Calculate the position of the window in the screen based on the window geometry
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen_center)

        # Mover the window to this position
        self.move(window_rect.topLeft())

    def on_btnStart(self):
        ### Example of accessing element ###
        # print(self.ResistancePanel.ResistanceSelection.child("Resistance 0").child("DAQ_CODE").value())

        i = 0
        resistance_list = []

        for child in self.ResistancePanel.ResistanceSelection.children():
            if child.value():  # Si hem seleccionat la resistència, l'afegim a la llista
                resistance_list.append(parameter_to_dict(child))
                resistance_list[i]["RLOAD_ID"] = child.name()
                resistance_list[i]["DAQ_CODE"] = [int(bit) for bit in resistance_list[i]["DAQ_CODE"]]
                i += 1

        if len(resistance_list) != 0:
            # Avisem a l'usuari que comencen les mesures
            print("Starting Measurements")

            # Setting to default the Manual Triggering and the LinMot Trigger
            self.LinMotControl.LinMotTrigger_Parameter.setValue(False)
            for param in self.ResistancePanel.ManualTriggering.children():
                param.setValue(False)

            # Disable buttons
            for button in self.mainWindowButtons.values():
                button.setEnabled(False)

            # Disable the experiment configuration interface
            for parameterGroup in self.mainWindowParamGroups.values():
                set_group_readonly(parameterGroup, True)

            self.AcquisitionProgram = AcquisitionProgram(CHANNELS=self.CHANNELS, RESISTANCE_DATA=resistance_list,
                                                         mainWindowButtons=self.mainWindowButtons,
                                                         mainWindowParamGroups=self.mainWindowParamGroups,
                                                         automatic_mode=True,
                                                         RelayCodeTask=self.DO_task_RelayCode,
                                                         LinMotTriggerTask=self.DO_task_LinMotTrigger,
                                                         measure_time=self.RecordingParameters.MeasuringTimeParameter.value(),
                                                         SAMPLE_RATE=self.RecordingParameters.SamplingRateParameter.value(),
                                                         SAMPLES_PER_CALLBACK=self.RecordingParameters.SAMPLES_PER_CALLBACK_Parameter.value(),
                                                         CALLBACKS_PER_BUFFER=self.RecordingParameters.CALLBACKS_PER_BUFFER_Parameter.value(),
                                                         TimeWindowLength=self.RecordingParameters.TimeWindowLenghtParameter.value(),
                                                         refresh_rate=self.RecordingParameters.RefreshRateParameter.value(),
                                                         LinMotTriggerLine=self.RecordingParameters.LinMotTriggerLineParameter.value(),
                                                         PrepareRaspberryLine=self.RecordingParameters.PrepareRaspberryLineParameter.value(),
                                                         RaspberryStatus_0_Line=self.RecordingParameters.RaspberryStatus_0_LineParameter.value(),
                                                         RaspberryStatus_1_Line=self.RecordingParameters.RaspberryStatus_1_LineParameter.value(),
                                                         RelayCodeLines=self.RecordingParameters.RelayCodeLinesParameter.value()
                                                         )
            self.AcquisitionProgram.show()
        else:
            print("There are no resistances to measure")


    def on_loadParameters(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Fitxer", "", "Tots els fitxers (*)",
                                                   options=options)
        if file_path:  # Si hem seleccionat un fitxer
            self.file_path = file_path
            print(f"Selected file: {file_path}")
        else:
            return

        dictionary_parameters = read_excel(file_path = file_path)

        # Update ParameterGroup ResistancePanel
        self.ResistancePanel = ResistancePanel(DO_task_RelayCode=self.DO_task_RelayCode,
                                               dictionary_parameters=dictionary_parameters,
                                               name='Resistance Panel',
                                               title='Resistance Panel')

        # Update the reference of mainWindowParamGroups
        self.mainWindowParamGroups["ResistancePanel"] = self.ResistancePanel

        # Set the new configuration
        self.ParameterTree_ControlPanel.setParameters(self.ResistancePanel)
        self.ParameterTree_ControlPanel.addParameters(self.LinMotControl)
        self.ParameterTree_ControlPanel.addParameters(self.RecordingParameters)

        # Activate sigValueChanged events after initialization
        self.ResistancePanel.ManualTriggering.initialized_success()


    def closeEvent(self, event):
        if self.AcquisitionProgram:
            if self.AcquisitionProgram.isVisible():
                self.AcquisitionProgram.close()

        self.DO_task_LinMotTrigger.StopTask()
        self.DO_task_LinMotTrigger.ClearTask()

        self.DO_task_RelayCode.StopTask()
        self.DO_task_RelayCode.ClearTask()

        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()