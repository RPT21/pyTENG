import pyqtgraph.parametertree.parameterTypes as pTypes
from PyQt5 import Qt
from pyqtgraph.parametertree import Parameter, ParameterTree

class ResistanceSelection(pTypes.GroupParameter):
    # Es equivalent a fer Parameter(type="group", ...)
    def __init__(self, **kwargs):
        super(ResistanceSelection, self).__init__(**kwargs)
        self.default_dict = {'NAME': ['Resistance 0', 'Resistance 1', 'Resistance 2', 'Resistance 3', 'Resistance 4', 'Resistance 5', 'Resistance 6', 'Resistance 7', 'Resistance 8', 'Resistance 9', 'Resistance 10', 'Resistance 11', 'Resistance 12', 'Resistance 13', 'Resistance 14', 'Resistance 15'],
                        'VALUE': [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80],
                        'CODE': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                        'ATENUATION': [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0]}

        # Inicialitzem els parametres per defecte:
        parameters = list()
        dict_keys = list(self.default_dict.keys())
        rows = len(self.default_dict[dict_keys[0]])
        columns = len(dict_keys)

        for n in range(rows):
            main_name = self.default_dict[dict_keys[0]][n]
            children_parametres = list()
            for m in range(1, columns):
                children_name = dict_keys[m]
                children_value = self.default_dict[dict_keys[m]][n]
                children_parameter = Parameter.create(**{'name': children_name,
                                                         'title': children_name,
                                                         'type': 'float',
                                                         'value': children_value,
                                                         'expanded': False,
                                                         'readonly': True})
                children_parametres.append(children_parameter)

            self.addChild({'name': main_name,
                        'title': main_name,
                        'type': 'bool',
                        'expanded': False,
                        'children': children_parametres})