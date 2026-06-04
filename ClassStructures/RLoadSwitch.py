# Importing PyQt(5 or 6 version) from qtpy (compatibility abstraction layer for different PyQt versions)
# PyQt5 is an adapted version of C/C++ Qt framework for python to do GUI applications
from qtpy import QtWidgets
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFileDialog, QPushButton, QDesktopWidget, QMessageBox

# Importing pyqtgraph (module of C/C++ Qt framework) to do ParameterTree widgets and plotting
from pyqtgraph.parametertree import ParameterTree
from pyqtgraph.parametertree import Parameter

# Importing custom classes and functions
from utils.ReadExcel import read_excel
from TreeStructures.ResistancePanel import ResistancePanel
from TreeStructures.LinMotControl import LinMotControl
from TreeStructures.RecordingParameters import RecordingParameters
from ClassStructures.MeasurementCore import AcquisitionProgram
from ClassStructures.DaqInterface import DigitalOutputTask_MultipleChannels, DigitalOutputTask


class R_LOAD_SWITCH(QWidget):
    ''' Main Window '''

    def __init__(self,
                 METADATA_COLUMNS,
                 R_LOAD_PROFILE,
                 RelayCodeLines="Dev1/port0/line0:5",
                 LinMotTriggerLine="Dev1/port0/line7",
                 tribu_id=None,
                 sample_id_neg=None,
                 sample_id_pos=None):
        super(R_LOAD_SWITCH, self).__init__()
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

        self.groupBox_ExperimentParams = QGroupBox("Experiment Parameters")
        self.blockLayout_ExperimentParams = QVBoxLayout()
        self.groupBox_ExperimentParams.setLayout(self.blockLayout_ExperimentParams)
        self.groupBox_ExperimentParams.setMinimumHeight(120)
        self.groupBox_ExperimentParams.setMaximumHeight(220)
        self.groupBox_ExperimentParams.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                     QtWidgets.QSizePolicy.Expanding)

        # Connect to DAQ:
        self.RelayCodeLines = RelayCodeLines
        self.LinMotTriggerLine = LinMotTriggerLine
        self.DO_task_RelayCode = DigitalOutputTask_MultipleChannels(channels=self.RelayCodeLines)
        self.DO_task_LinMotTrigger = DigitalOutputTask(line=self.LinMotTriggerLine)

        # Definim el ParameterTree
        self.ParameterTree_ControlPanel = ParameterTree()

        # Definim el ParameterTree for experiment parameters
        self.ParameterTree_ExperimentParams = ParameterTree()
        self.ParameterTree_ExperimentParams.setMinimumHeight(90)
        self.ParameterTree_ExperimentParams.setMaximumHeight(180)
        self.ParameterTree_ExperimentParams.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                          QtWidgets.QSizePolicy.Expanding)
        self.ExperimentParams = Parameter.create(
            name="Experiment Parameters",
            type="group",
            children=[
                {"name": "TribuId", "type": "str", "value": ""},
                {"name": "SampleIdTriboNeg", "type": "str", "value": ""},
                {"name": "SampleIdTriboPos", "type": "str", "value": ""},
            ],
        )
        self.ParameterTree_ExperimentParams.setParameters(self.ExperimentParams, showTop=False)

        if tribu_id is not None:
            self.ExperimentParams.child("TribuId").setValue(str(tribu_id))
        if sample_id_neg is not None:
            self.ExperimentParams.child("SampleIdTriboNeg").setValue(str(sample_id_neg))
        if sample_id_pos is not None:
            self.ExperimentParams.child("SampleIdTriboPos").setValue(str(sample_id_pos))

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

        # Afegim el ParameterTree dels paràmetres d'experiment
        self.blockLayout_ExperimentParams.addWidget(self.ParameterTree_ExperimentParams)

        # Afegim el GroupBox al layout de la GUI
        self.layout.addWidget(self.groupBox_ControlPanel)
        self.layout.addWidget(self.groupBox_ExperimentParams)
        self.layout.setStretchFactor(self.groupBox_ControlPanel, 2)
        self.layout.setStretchFactor(self.groupBox_ExperimentParams, 1)

        # Acquisition Program Inputs
        self.METADATA_COLUMNS = METADATA_COLUMNS
        self.R_LOAD_PROFILE = R_LOAD_PROFILE

        # Build DAQ_PROFILES mapping
        self.DAQ_PROFILES = {
            "VR": self.R_LOAD_PROFILE,
        }

        self.AcquisitionProgram = None

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
                resistance_list.append(self._parameter_to_dict(child))
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

            sampling_rate = self.RecordingParameters.SamplingRateParameter.value()
            if sampling_rate <= 0:
                print("Sampling Rate must be > 0")
                return

            daq_usb_transfer_frequency = self.RecordingParameters.DAQ_USB_TRANSFER_FREQUENCY_Parameter.value()
            buffer_saving_time_interval = self.RecordingParameters.BUFFER_SAVING_TIME_INTERVAL_Parameter.value()

            if daq_usb_transfer_frequency <= 0:
                print("DAQ USB Transfer Frequency must be > 0")
                return
            if buffer_saving_time_interval <= 0:
                print("Buffer Saving Time Interval must be > 0")
                return

            refresh_rate_hz = self.RecordingParameters.RefreshRateParameter.value()
            if refresh_rate_hz <= 0:
                print("Refresh Rate must be > 0")
                return

            tribu_id = self.ExperimentParams.child("TribuId").value()
            sample_id_neg = self.ExperimentParams.child("SampleIdTriboNeg").value()
            sample_id_pos = self.ExperimentParams.child("SampleIdTriboPos").value()

            missing_fields = []
            if not str(tribu_id).strip():
                missing_fields.append("TribuId")
            if not str(sample_id_neg).strip():
                missing_fields.append("SampleIdTriboNeg")
            if not str(sample_id_pos).strip():
                missing_fields.append("SampleIdTriboPos")

            if missing_fields:
                QMessageBox.critical(
                    self,
                    "Missing Experiment Parameters",
                    "Please fill in: " + ", ".join(missing_fields)
                )
                return

            self.AcquisitionProgram = AcquisitionProgram(METADATA_COLUMNS=self.METADATA_COLUMNS,
                                                         DAQ_PROFILES=self.DAQ_PROFILES,
                                                         RESISTANCE_DATA=resistance_list,
                                                         automatic_mode=True,
                                                         RelayCodeTask=self.DO_task_RelayCode,
                                                         LinMotTriggerTask=self.DO_task_LinMotTrigger,
                                                         measure_time=self.RecordingParameters.MeasuringTimeParameter.value(),
                                                         DAQ_USB_TRANSFER_FREQUENCY=daq_usb_transfer_frequency,
                                                         BUFFER_SAVING_TIME_INTERVAL=buffer_saving_time_interval,
                                                         TimeWindowLength=self.RecordingParameters.TimeWindowLenghtParameter.value(),
                                                         ScreenRefreshFrequency=refresh_rate_hz,
                                                         LinMotTriggerLine=self.RecordingParameters.LinMotTriggerLineParameter.value(),
                                                         PrepareRaspberryLine=self.RecordingParameters.PrepareRaspberryLineParameter.value(),
                                                         RaspberryStatus_0_Line=self.RecordingParameters.RaspberryStatus_0_LineParameter.value(),
                                                         RaspberryStatus_1_Line=self.RecordingParameters.RaspberryStatus_1_LineParameter.value(),
                                                         RelayCodeLines=self.RecordingParameters.RelayCodeLinesParameter.value(),
                                                         tribu_id=tribu_id,
                                                         SampleIdTriboNeg=sample_id_neg,
                                                         SampleIdTriboPos=sample_id_pos,
                                                         use_keithley=False,
                                                         use_raspberry=True,
                                                         parent=self
                                                         )
            self.AcquisitionProgram.exec_()
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

    def _parameter_to_dict(self, param):
        result = {}
        for child in param.children():
            if child.children():
                # If it has more children inside, do recursive calls
                result[child.name()] = self.parameter_to_dict(child)
            else:
                result[child.name()] = child.value()
        return result