import pyqtgraph.parametertree.parameterTypes as pTypes
from PyQt5 import Qt
from pyqtgraph.parametertree import Parameter, ParameterTree

class LinMotControl(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, **kwargs):

        super(LinMotControl, self).__init__(**kwargs)

        self.addChild({'name': "Enable Trigger",
                                        'title': "Enable Trigger",
                                        'type': 'bool',
                                        'expanded': True})
