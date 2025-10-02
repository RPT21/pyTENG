# Importing PyQt(5 or 6 version) from qtpy (compatibility abstraction layer for different PyQt versions)
# PyQt5 is an adapted version of C/C++ Qt framework for python to do GUI applications
from qtpy import QtWidgets
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFileDialog, QPushButton

# Importing pyqtgraph (module of C/C++ Qt framework) to do ParameterTree widgets and plotting
from pyqtgraph.parametertree import Parameter, ParameterTree

# Accessing python interpreter variables and functions
import sys

# Importing custom classes and functions
from ReadExcel import read_excel
from TreeStructures.ResistancePanel import ResistancePanel
from TreeStructures.LinMotControl import LinMotControl
from TreeStructures.RecordingParameters import RecordingParameters
from MeasurementCore import AdquisitionProgram

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


class MainWindow(QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()
        self.layout = QVBoxLayout(self)

        self.setGeometry(650, 20, 450, 1000)
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

        # Definim el ParameterTree
        self.ParameterTree_ControlPanel = ParameterTree()

        # Definim el ParameterGroup ResistancePanel
        self.ResistancePanel = ResistancePanel(name='Resistance Panel',
                                               title='Resistance Panel')

        # Definim el ParameterGroup LinMotControl
        self.LinMotControl = LinMotControl(name='LinMot Control',
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
        self.CHANNELS = {
            "LinMot_Enable": ["Dev1/ai0", DAQmx_Val_RSE, 0],
            "LinMot_Up_Down": ["Dev1/ai1", DAQmx_Val_RSE, 1],
            "Voltage": ["Dev1/ai2", DAQmx_Val_Diff, 2],
            "Current": ["Dev1/ai3", DAQmx_Val_RSE, 3]
        }


    def on_btnStart(self):
        # Example of accessing element
        # print(self.ResistancePanel.ResistanceSelection.child("Resistance 0").child("DAQ_CODE").value())

        # Preparem els diccionaris amb les mesures que volem fer i els seus paràmetres
        recording_parameters_dict = parameter_to_dict(self.RecordingParameters)

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
            self.btnAcq.setEnabled(False)
            self.btnLoad.setEnabled(False)
            self.AdquisitionProgram = AdquisitionProgram(CHANNELS=self.CHANNELS, RESISTANCE_DATA=resistance_list,
                                                         AcqButton=self.btnAcq,
                                                         LoadButton=self.btnLoad,
                                                         automatic_mode=True)
            self.AdquisitionProgram.show()
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

        # Actualitzem el ParameterGroup ResistancePanel
        self.ResistancePanel = ResistancePanel(dictionary_parameters,
                                            name='Resistance Panel',
                                            title='Resistance Panel')


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()