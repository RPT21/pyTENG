from PyQt5 import Qt
from qtpy import QtWidgets
from DAQTest import *
from ReadExcel import read_excel
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGroupBox, QHBoxLayout, QLabel, QFileDialog
from pyqtgraph.parametertree import Parameter, ParameterTree
from TreeStructures.ResistancePanel import ResistancePanel
from TreeStructures.LinMotControl import LinMotControl
from TreeStructures.RecordingParameters import RecordingParameters
from MeasurementCore import MeasurementCore

# Funció per convertir el Parameter en un diccionari
def parameter_to_dict(param):
    result = {}
    for child in param.children():
        if child.children():
            # Si el fill té més fills, fem una trucada recursiva
            result[child.name()] = parameter_to_dict(child)
        else:
            result[child.name()] = child.value()
    return result


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()
        self.layout = Qt.QVBoxLayout(self)

        self.setGeometry(650, 20, 450, 1000)
        self.setWindowTitle('TENG Control Software')

        # Add objects to main window

        # start Button
        self.btnAcq = Qt.QPushButton("Start Measure")
        self.layout.addWidget(self.btnAcq)

        # load Button
        self.btnLoad = Qt.QPushButton("Load Parameters")
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

        # Definim la màquina d'estats per efectuar les mesures i la inicialitzem
        self.MeasurementCore = MeasurementCore()

    def on_btnStart(self):
        # Example of accessing element
        # print(self.ResistancePanel.ResistanceSelection.child("Resistance 0").child("DAQ_CODE").value())

        if not self.MeasurementCore.xRunning:

            # Avisem a l'usuari que comencen les mesures
            print("Starting Measurements")
            self.btnAcq.setText('Stop Measure')

            # Preparem els diccionaris amb les mesures que volem fer i els seus paràmetres
            recording_parameters_dict = parameter_to_dict(self.RecordingParameters)
            resistance_list = []
            for child in self.ResistancePanel.ResistanceSelection.children():
                if child.value():  # Si hem seleccionat la resistència, l'afegim a la llista
                    resistance_list.append(parameter_to_dict(child))

            if len(resistance_list) != 0:
                self.MeasurementCore.startMeasuring(Resistance_list=resistance_list,
                                                   Recording_Configuration=recording_parameters_dict)

        else:
            print("Stopping Measurements")
            self.btnAcq.setText('Start Measure')
            self.MeasurementCore.stop()

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