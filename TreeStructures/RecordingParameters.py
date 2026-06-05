import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter

class RecordingParameters(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, **kwargs):
        super(RecordingParameters, self).__init__(**kwargs)

        self.MeasuringTimeParameter = Parameter.create(**{'name': "Measuring Time",
                                                         'title': "Measuring Time",
                                                         'type': 'int',
                                                         'value': 5,
                                                         'expanded': True,
                                                         'step': 1,
                                                         'suffix': 's',
                                                         'limits': (0, None)})

        self.DAQ_USB_TRANSFER_FREQUENCY_Parameter = Parameter.create(**{'name': "DAQ_USB_TRANSFER_FREQUENCY",
                                                           'title': "DAQ USB Transfer Frequency",
                                                           'type': 'int',
                                                           'value': 60,
                                                           'expanded': True,
                                                           'step': 1,
                                                           'suffix': 'Hz',
                                                           'limits': (1, None)})

        self.BUFFER_SAVING_TIME_INTERVAL_Parameter = Parameter.create(**{'name': "BUFFER_SAVING_TIME_INTERVAL",
                                                           'title': "Buffer Saving Time Interval",
                                                           'type': 'float',
                                                           'value': 2.5,
                                                           'expanded': True,
                                                           'step': 0.1,
                                                           'suffix': 's',
                                                           'limits': (0.1, None)})

        self.TimeWindowLenghtParameter = Parameter.create(**{'name': "TimeWindowLenght",
                                                          'title': "TimeWindowLenght",
                                                          'type': 'int',
                                                          'value': 3,
                                                          'expanded': True,
                                                          'step': 1,
                                                          'suffix': 's',
                                                          'limits': (0, None)})

        self.RefreshRateParameter = Parameter.create(**{'name': "Refresh Rate",
                                                          'title': "Refresh Rate",
                                                          'type': 'int',
                                                          'value': 60,
                                                          'expanded': True,
                                                          'step': 1,
                                                          'suffix': 'Hz',
                                                          'limits': (1, None)})

        self.LinMotTriggerLineParameter = Parameter.create(**{'name': "LinMotTriggerLine",
                                                          'title': "LinMotTriggerLine",
                                                          'type': 'str',
                                                          'value': "Dev1/port0/line7",
                                                          'expanded': True})

        self.PrepareRaspberryLineParameter = Parameter.create(**{'name': "PrepareRaspberryLine",
                                                          'title': "PrepareRaspberryLine",
                                                          'type': 'str',
                                                          'value': "Dev1/port0/line6",
                                                          'expanded': True})

        self.RaspberryStatus_0_LineParameter = Parameter.create(**{'name': "RaspberryStatus_0_Line",
                                                          'title': "RaspberryStatus_0_Line",
                                                          'type': 'str',
                                                          'value': "Dev1/port1/line0",
                                                          'expanded': True})

        self.RaspberryStatus_1_LineParameter = Parameter.create(**{'name': "RaspberryStatus_1_Line",
                                                          'title': "RaspberryStatus_1_Line",
                                                          'type': 'str',
                                                          'value': "Dev1/port1/line1",
                                                          'expanded': True})

        self.RelayCodeLinesParameter = Parameter.create(**{'name': "RelayCodeLines",
                                                          'title': "RelayCodeLines",
                                                          'type': 'str',
                                                          'value': "Dev1/port0/line0:5",
                                                          'expanded': True})

        self.addChild(self.MeasuringTimeParameter)
        self.addChild(self.DAQ_USB_TRANSFER_FREQUENCY_Parameter)
        self.addChild(self.BUFFER_SAVING_TIME_INTERVAL_Parameter)
        self.addChild(self.TimeWindowLenghtParameter)
        self.addChild(self.RefreshRateParameter)
        self.addChild(self.LinMotTriggerLineParameter)
        self.addChild(self.PrepareRaspberryLineParameter)
        self.addChild(self.RaspberryStatus_0_LineParameter)
        self.addChild(self.RaspberryStatus_1_LineParameter)
        self.addChild(self.RelayCodeLinesParameter)
