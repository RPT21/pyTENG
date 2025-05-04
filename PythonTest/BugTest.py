import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph as pg
print("PyQtGraph version:", pg.__version__)

app = QApplication(sys.argv)

# --- Create a valid type='list' parameter ---
param_def = Parameter.create(name='params', type='group', children=[
    {'name': 'BoardSel', 'type': 'list', 'limits': ['uno', 'mega', 'nano'], 'value': 'mega'}
])

# Verify that it has a valid value
print("BEFORE calling setParameters:")
print("  BoardSel value:", param_def.param('BoardSel').value())  # should print "mega"

# --- Create the Parameter Tree ---
win = QWidget()
layout = QVBoxLayout()
tree = ParameterTree()
layout.addWidget(tree)
win.setLayout(layout)
win.show()

# --- Load param_def to Parameter Tree ---
tree.setParameters(param_def, showTop=False)

# Verify the value after loading it to the Parameter Tree
print("AFTER calling setParameters:")
print("  BoardSel value:", param_def.param('BoardSel').value())  # In older versions this is '' (bug error)

sys.exit(app.exec_())