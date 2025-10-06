import pyqtgraph.parametertree.parameterTypes as pTypes

class LinMotControl(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, DO_task_LinMotTrigger, **kwargs):

        super(LinMotControl, self).__init__(**kwargs)

        self.initializing = True
        self.selected_param = None
        self.xchanged = False
        self.DO_task_LinMotTrigger = DO_task_LinMotTrigger


        self.addChild({'name': "Enable Trigger",
                                        'title': "Enable Trigger",
                                        'type': 'bool',
                                        'expanded': True})

        self.register_callbacks("LinMot Control")

    def register_callbacks(self, block_name):
        """Recorre todos los parámetros y conecta sigValueChanged para imprimir cambios."""
        for param in self.children():
            self.register_recursive_callbacks(param, block_name)

    def register_recursive_callbacks(self, param, block_name):
        """Registra la señal sigValueChanged para un parámetro y sus hijos."""
        # sigValueChanged al connectar-lo a una funció, la truca enviant-li dos parametres: param, value.
        # Si volem que la funcio connectada accepti més parametres, utilitzem la funció lambda, la qual recull
        # els dos parametres, i els redirigeix a la funcio que volem afegir els paràmetres addicionals.
        param.sigValueChanged.connect(lambda param, value: self.parameter_changed(param, value, block_name))

        if param.type() == 'group':
            for child in param.children():
                self.register_recursive_callbacks(child, block_name)

    def parameter_changed(self, param, value, block_name):
        """Función que se llama cuando un parámetro cambia."""
        if not self.initializing:
            if value and self.selected_param is not param:
                if self.selected_param:
                    self.xchanged = True
                    self.selected_param.setValue(0)
                self.selected_param = param
                print(f"[{block_name}] '{param.name()}' selected")
                self.DO_task_LinMotTrigger.set_line(1)
                return

            elif not value and self.selected_param is param and not self.xchanged:
                self.selected_param = None
                self.DO_task_LinMotTrigger.set_line(0)
                print(f"[{block_name}] '{param.name()}' disabled")

            self.xchanged = False


    def initialized_success(self):
        self.initializing = False