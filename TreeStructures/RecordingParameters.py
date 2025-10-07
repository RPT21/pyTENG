import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter

class RecordingParameters(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, **kwargs):
        super(RecordingParameters, self).__init__(**kwargs)

        self.SamplingRateParameter = Parameter.create(**{'name': "Sampling Rate",
                                        'title': "Sampling Rate",
                                        'type': 'int',
                                        'value': 10000,
                                        'expanded': True,
                                        'step': 100,
                                        'suffix': 'Hz',
                                        'limits': (0, 100000)})

        self.MeasuringTimeParameter = Parameter.create(**{'name': "Measuring Time",
                                                         'title': "Measuring Time",
                                                         'type': 'int',
                                                         'value': 30,
                                                         'expanded': True,
                                                         'step': 1,
                                                         'suffix': 's',
                                                         'limits': (0, None)})

        self.SAMPLES_PER_CALLBACK_Parameter = Parameter.create(**{'name': "SAMPLES_PER_CALLBACK",
                                                          'title': "SAMPLES_PER_CALLBACK",
                                                          'type': 'int',
                                                          'value': 100,
                                                          'expanded': True,
                                                          'step': 1,
                                                          'limits': (0, None)})

        self.CALLBACKS_PER_BUFFER_Parameter = Parameter.create(**{'name': "CALLBACKS_PER_BUFFER",
                                                          'title': "CALLBACKS_PER_BUFFER",
                                                          'type': 'int',
                                                          'value': 500,
                                                          'expanded': True,
                                                          'step': 1,
                                                          'limits': (0, None)})

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
                                                          'value': 10,
                                                          'expanded': True,
                                                          'step': 1,
                                                          'suffix': 'ms',
                                                          'limits': (0, None)})

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

        self.addChild(self.SamplingRateParameter)
        self.addChild(self.MeasuringTimeParameter)
        self.addChild(self.SAMPLES_PER_CALLBACK_Parameter)
        self.addChild(self.CALLBACKS_PER_BUFFER_Parameter)
        self.addChild(self.TimeWindowLenghtParameter)
        self.addChild(self.RefreshRateParameter)
        self.addChild(self.LinMotTriggerLineParameter)
        self.addChild(self.PrepareRaspberryLineParameter)
        self.addChild(self.RaspberryStatus_0_LineParameter)
        self.addChild(self.RaspberryStatus_1_LineParameter)
        self.addChild(self.RelayCodeLinesParameter)

