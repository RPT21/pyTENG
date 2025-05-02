import pyqtgraph.parametertree.parameterTypes as pTypes

class RecordingParameters(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, **kwargs):
        super(RecordingParameters, self).__init__(**kwargs)

        self.addChild({'name': "Sampling Rate",
                                        'title': "Sampling Rate",
                                        'type': 'int',
                                        'value': 1000,
                                        'expanded': True,
                                        'step': 100,
                                        'suffix': 'Hz',
                                        'limits': (0, 10000)})
