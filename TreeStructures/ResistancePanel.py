import pyqtgraph.parametertree.parameterTypes as pTypes
from PyQt5 import Qt
from pyqtgraph.parametertree import Parameter, ParameterTree

class ResistanceSelection(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, dictionary_parameters, **kwargs):

        super(ResistanceSelection, self).__init__(**kwargs)

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
                                                         'type': 'float' if children_name is not "DAQ_CODE" else 'str',
                                                         'value': children_value,
                                                         'expanded': False,
                                                         'readonly': True})
                children_parametres.append(children_parameter)

            self.addChild({'name': main_name,
                        'title': main_name,
                        'type': 'bool',
                        'expanded': False,
                        'children': children_parametres})


class ManualTriggering(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, dictionary_parameters, **kwargs):
        super(ManualTriggering, self).__init__(**kwargs)

        dict_keys = list(dictionary_parameters.keys())
        rows = len(dictionary_parameters[dict_keys[0]])
        columns = len(dict_keys)

        for n in range(rows):
            main_name = dictionary_parameters[dict_keys[0]][n]
            children_parametres = list()

            self.addChild({'name': main_name,
                        'title': main_name,
                        'type': 'bool',
                        'expanded': True})

        # Conectar eventos de cambio
        self.register_callbacks("Manual Triggering")

    def register_callbacks(self, block_name):
        """Recorre todos los parámetros y conecta sigValueChanged para imprimir cambios."""
        for param in self.children():
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
        print(f"[{block_name}] '{param.name()}' changed to: {value}")
        if value:
            # Si uno se activa (se pone en True), desactivar los demás
            for other_param in self.children():
                if other_param is not param:
                    other_param.setValue(False)


class ResistancePanel(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, dictionary_parameters = None, **kwargs):

        super(ResistancePanel, self).__init__(**kwargs)


        self.default_dict = {
        'NAME': ['Resistance 0', 'Resistance 1', 'Resistance 2', 'Resistance 3', 'Resistance 4', 'Resistance 5',
                 'Resistance 6', 'Resistance 7', 'Resistance 8', 'Resistance 9', 'Resistance 10', 'Resistance 11',
                 'Resistance 12', 'Resistance 13', 'Resistance 14', 'Resistance 15', 'Resistance 16', 'Resistance 17',
                 'Resistance 18', 'Resistance 19', 'Resistance 20', 'Resistance 21', 'Resistance 22', 'Resistance 23'],
        'VALUE': [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120],
        'ATENUATION': [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.2, 4.4, 4.6,
                        4.8, 5.0, 5.2, 5.4, 5.6],
        'DAQ_CODE': ['000001', '001001', '010001', '011001', '100001', '101001', '110001', '111001', '000010',
                     '001010', '010010', '011010', '100010', '101010', '110010', '111010', '000100', '001100',
                     '010100', '011100', '100100', '101100', '110100', '111100']}

        if dictionary_parameters is None:
            dictionary_parameters = self.default_dict

        # Definim el ParameterGroup ResistanceSelection
        self.ResistanceSelection = ResistanceSelection(dictionary_parameters,
                                                       name='Resistance Selection',
                                                       title='Resistance Selection')
        # Definim el ParameterGroup ManualTriggering
        self.ManualTriggering = ManualTriggering(dictionary_parameters,
                                                 name='Manual Triggering',
                                                 title='Manual Triggering')

        self.addChild(self.ResistanceSelection)
        self.addChild(self.ManualTriggering)
