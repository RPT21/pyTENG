import PyDAQmx as Daq
import sys
import ctypes
from ctypes import byref, c_int32
from PyQt5 import Qt
from qtpy import QtWidgets
from DAQTest import *
from ReadExcel import read_excel
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGroupBox, QHBoxLayout, QLabel, QFileDialog
from pyqtgraph.parametertree import Parameter, ParameterTree
from TreeStructures.ResistanceSelection import ResistanceSelection
from TreeStructures.ManualTriggering import ManualTriggering

class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()
        self.layout = Qt.QVBoxLayout(self)
        self.xRunning = False
        self.task = CallbackTask()

        self.setGeometry(650, 20, 450, 1200)
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

        # ////////////////////// Inicialització dels primers dos group boxs /////////////////////////

        self.groupBox = QGroupBox("Resistance Panel")
        self.blockLayout = QVBoxLayout()
        self.groupBox.setLayout(self.blockLayout)

        # Crear el árbol de parámetros
        self.ParameterTree_ResistancePanel = ParameterTree()

        # Afegim al ParameterTree la ResistanceSelection
        self.ResistanceSelection = ResistanceSelection(name='Resistance Selection',
                                       title='Resistance Selection')
        self.ParameterTree_ResistancePanel.addParameters(self.ResistanceSelection)

        # Afegim al ParameterTree el ManualTriggering
        self.ManualTriggering = ManualTriggering(name='Manual Triggering',
                                                       title='Manual Triggering')
        self.ParameterTree_ResistancePanel.addParameters(self.ManualTriggering)

        self.ParameterTree_ResistancePanel.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.ParameterTree_ResistancePanel.setColumnWidth(0, 200)

        # Afegim el ParameterTree al layout del GroupBox
        self.blockLayout.addWidget(self.ParameterTree_ResistancePanel)

        # Afegim el GroupBox al layout de la GUI
        self.layout.addWidget(self.groupBox)

        # /////////////////////// Tercer groupBox - LinMot Trigger ///////////////////////////////////
        # Afegim el linMot Drive Trigger
        groupBox = QGroupBox("LinMot Control")
        blockLayout = QVBoxLayout()
        groupBox.setLayout(blockLayout)

        parameters = list()
        parameter = Parameter.create(**{'name': "Enable Trigger",
                                        'title': "Enable Trigger",
                                        'type': 'bool',
                                        'expanded': True})
        parameters.append(parameter)

        # Crear el parámetro raíz (es un grupo global)
        self.LinMotControl = Parameter.create(name='params', type='group', children=parameters)

        # Crear el árbol de parámetros
        self.tree_LinMotControl = ParameterTree()
        self.tree_LinMotControl.setParameters(self.LinMotControl, showTop=False)

        # Añadir el árbol al layout
        blockLayout.addWidget(self.tree_LinMotControl)

        groupBox.setMaximumSize(450, 150)

        self.layout.addWidget(groupBox)

        # /////////////////////// Quart groupBox - Recording Parameters ///////////////////////////////////
        groupBox = QGroupBox("Recording Parameters")
        blockLayout = QVBoxLayout()
        groupBox.setLayout(blockLayout)

        parameters = list()
        parameter = Parameter.create(**{'name': "Sampling Rate",
                                               'title': "Sampling Rate",
                                               'type': 'int',
                                               'value': 1000,
                                               'expanded': True,
                                               'step': 100,
                                               'suffix': 'Hz',
                                               'limits': (0,10000)})
        parameters.append(parameter)

        # Crear el parámetro raíz (es un grupo global)
        self.param_root_recording = Parameter.create(name='params', type='group', children=parameters)

        # Crear el árbol de parámetros
        self.tree_recordingParam = ParameterTree()
        self.tree_recordingParam.setParameters(self.param_root_recording, showTop=False)

        self.tree_recordingParam.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.tree_recordingParam.setColumnWidth(0, 200)

        # Añadir el árbol al layout
        blockLayout.addWidget(self.tree_recordingParam)

        groupBox.setMinimumSize(450, 200)
        self.layout.addWidget(groupBox)


    def on_btnStart(self):
        if not self.xRunning:
            print("Start Measure")
            self.task.StartTask()
            self.btnAcq.setText('Stop Measure')
            self.xRunning = True
        else:
            print("Stop Measure")
            self.task.StopTask()
            self.btnAcq.setText('Start Measure')
            self.xRunning = False

    def on_loadParameters(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo", "", "Todos los archivos (*)",
                                                   options=options)
        if file_path:  # Si seleccionó un archivo
            self.file_path = file_path
            print(f"Selected file: {file_path}")
        else:
            return

        dictionary_parameters = read_excel(file_path = file_path)

        # /////////////////////// Primer groupBox - Selector de resistencies a medir ///////////////////////////////////

        parameters = list()
        dict_keys = list(dictionary_parameters.keys())
        rows = len(dictionary_parameters[dict_keys[0]])
        columns = len(dict_keys)

        for n in range(rows):
            main_name = dictionary_parameters[dict_keys[0]][n]
            children_parametres = list()
            for m in range(1, columns):
                children_name = dict_keys[m]
                children_value = dictionary_parameters[dict_keys[m]][n]
                children_parameter = Parameter.create(**{'name': children_name,
                                                         'title': children_name,
                                                         'type': 'float',
                                                         'value': children_value,
                                                         'expanded': True,
                                                         'readonly': True})
                children_parametres.append(children_parameter)

            parameter = Parameter.create(**{'name': main_name,
                                            'title': main_name,
                                            'type': 'bool',
                                            'expanded': True,
                                            'children': children_parametres})

            parameters.append(parameter)

        # Actualitzar l'arquitectura de paràmetres
        self.param_root = Parameter.create(name='params', type='group', children=parameters)

        # Actualitzar el Parameter Tree
        self.tree_resistances.setParameters(self.param_root, showTop=False)

        # /////////////////////// Segon groupBox - Trigger manual ///////////////////////////////////

        parameters = list()
        dict_keys = list(dictionary_parameters.keys())
        rows = len(dictionary_parameters[dict_keys[0]])
        columns = len(dict_keys)

        for n in range(rows):
            main_name = dictionary_parameters[dict_keys[0]][n]
            children_parametres = list()

            parameter = Parameter.create(**{'name': main_name,
                                            'title': main_name,
                                            'type': 'bool',
                                            'expanded': True})

            parameters.append(parameter)

        # Crear el parámetro raíz (es un grupo global)
        self.param_root_manual = Parameter.create(name='params', type='group', children=parameters)

        # Crear el árbol de parámetros
        self.tree_manual.setParameters(self.param_root_manual, showTop=False)

        # Conectar eventos de cambio
        self.register_callbacks(self.param_root_manual, "Manual Triggering")


    def register_callbacks(self, param_group, block_name):
        """Recorre todos los parámetros y conecta sigValueChanged para imprimir cambios."""
        for param in param_group.children():
            self.register_recursive_callbacks(param, block_name)

    def register_recursive_callbacks(self, param, block_name):
        """Registra la señal sigValueChanged para un parámetro y sus hijos."""
        # sigValueChanged al connectar-lo a una funció, la truca enviant-li dos parametres: param, value.
        # Si volem que la funcio connectada accepti més parametres, utilitzem la funció lambda, la qual recull
        # els dos parametres, i els redirigeix a la funcio que volem afegint els paràmetres addicionals.
        param.sigValueChanged.connect(lambda param, value: self.parameter_changed(param, value, block_name))

        if param.type() == 'group':
            for child in param.children():
                self.register_recursive_callbacks(child, block_name)

    def parameter_changed(self, param, value, block_name):
        """Función que se llama cuando un parámetro cambia."""
        print(f"[{block_name}] '{param.name()}' cambió a: {value}")
        if value:
            # Si uno se activa (se pone en True), desactivar los demás
            for other_param in self.param_root_manual.children():
                if other_param is not param:
                    other_param.setValue(False)

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()