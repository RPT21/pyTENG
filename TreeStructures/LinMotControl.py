import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter

class LinMotControl(pTypes.GroupParameter):
    # Equivalent to do Parameter(type="group", ...)
    def __init__(self, DO_task_LinMotTrigger, **kwargs):

        super(LinMotControl, self).__init__(**kwargs)

        self.initializing = True
        self.DO_task_LinMotTrigger = DO_task_LinMotTrigger

        self.LinMotTrigger_Parameter = Parameter.create(**{'name': "Enable Trigger",
                                        'title': "Enable Trigger",
                                        'type': 'bool',
                                        'expanded': True})

        self.addChild(self.LinMotTrigger_Parameter)

        block_name = "LinMot Control"
        self.LinMotTrigger_Parameter.sigValueChanged.connect(
            lambda param, value: self.parameter_changed(param, value, block_name))

    def parameter_changed(self, param, value, block_name):
        """Function called when a parameter is changed."""
        if not self.initializing:
            if value:
                print(f"[{block_name}] '{param.name()}' selected")
                self.DO_task_LinMotTrigger.set_line(1)
            else:
                self.DO_task_LinMotTrigger.set_line(0)
                print(f"[{block_name}] '{param.name()}' disabled")


    def initialized_success(self):
        self.initializing = False