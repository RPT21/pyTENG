from PyQt5.QtWidgets import (QPushButton, QVBoxLayout,
                             QHBoxLayout, QDialog, QPlainTextEdit)
from PyQt5.QtCore import pyqtSignal

from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem

class TextEditWidget(QPlainTextEdit):
    """QPlainTextEdit with sigChanged signal for compatibility with WidgetParameterItem."""
    sigChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.sigChanged.emit)

    def setValue(self, value):
        """Set the text of the widget."""
        if value is not None:
            self.setPlainText(str(value))
        else:
            self.setPlainText("")

    def value(self):
        """Return the current text value."""
        return self.toPlainText()

class TextParameterItem(WidgetParameterItem):
    """Custom parameter item that uses TextEditWidget for multi-line text input."""

    def makeWidget(self):
        w = TextEditWidget()
        w.setMaximumHeight(120)
        w.setMinimumHeight(100)
        initial_value = str(self.param.value()) if self.param.value() is not None else ""
        w.setPlainText(initial_value)
        w.sigChanged.connect(lambda: self.param.setValue(w.toPlainText()))
        return w

class TextParameter(Parameter):
    """Custom Parameter type for multi-line text."""
    itemClass = TextParameterItem

    def __init__(self, **opts):
        super().__init__(**opts)

class ExpConfigWindow(QDialog):
    def __init__(self, METADATA_COLUMNS, parent=None):
        super().__init__(parent)

        # Build the hidden Parameter group (not shown until dialog opens)
        children = []
        for col, meta in METADATA_COLUMNS.items():
            if col in ('Date', 'ReadingTime (s)'):
                continue  # Auto-generated and must not be editable in the dialog.
            ptype = meta.get('type', 'str')
            if ptype not in ('str', 'int', 'float', 'bool', 'list', 'text'):
                ptype = 'str'
            # Keep Notes as 'str' initially, will replace with TextParameter later
            default = meta.get('default', None)
            value = meta.get('value', None)
            limits = meta.get('limit', None)
            children.append({'name': col, 'type': ptype, 'value': value, 'default': default, "limits": limits})

        self.metadata_param_tree = Parameter.create(name='Experiment Parameters', type='group', children=children)

        # Replace Notes parameter with TextParameter for multi-line text
        notes_param = self.metadata_param_tree.param('Notes')
        if notes_param is not None:
            notes_value = notes_param.value()
            self.metadata_param_tree.removeChild(notes_param)
            text_param = TextParameter(name='Notes', type='text', value=notes_value)
            self.metadata_param_tree.addChild(text_param)

        self.METADATA_COLUMNS = METADATA_COLUMNS
        self._snapshot_values = {}

        self.setWindowTitle("Edit Experiment Parameters")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
                    QDialog {
                        background-color: #f5f7fb;
                    }
                    QLabel {
                        color: #1f2937;
                        font-size: 12px;
                        font-weight: 500;
                    }
                    QPushButton {
                        padding: 8px 16px;
                        border-radius: 4px;
                        border: none;
                        font-weight: 600;
                        font-size: 11px;
                        min-height: 32px;
                        min-width: 80px;
                    }
                    QPushButton#saveAction {
                        background-color: #2563eb;
                        color: white;
                    }
                    QPushButton#saveAction:hover {
                        background-color: #1d4ed8;
                    }
                    QPushButton#cancelAction {
                        background-color: #6b7280;
                        color: white;
                    }
                    QPushButton#cancelAction:hover {
                        background-color: #4b5563;
                    }
                """)

        dlg_layout = QVBoxLayout(self)
        dlg_layout.setContentsMargins(16, 16, 16, 16)
        dlg_layout.setSpacing(12)

        tree = ParameterTree()
        tree.setParameters(self.metadata_param_tree, showTop=True)
        dlg_layout.addWidget(tree)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.setObjectName("saveAction")
        btn_cancel.setObjectName("cancelAction")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        dlg_layout.addLayout(btn_layout)

        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        # Capture the current committed values as the initial rollback snapshot.
        self._capture_snapshot()

    def _iter_editable_columns(self):
        for col in self.METADATA_COLUMNS.keys():
            if col in ('Date', 'ReadingTime (s)'):
                continue
            yield col

    def _capture_snapshot(self):
        self._snapshot_values = {}
        for col in self._iter_editable_columns():
            param = self.metadata_param_tree.param(col)
            self._snapshot_values[col] = param.value() if param is not None else None

    def _restore_snapshot(self):
        for col, value in self._snapshot_values.items():
            param = self.metadata_param_tree.param(col)
            if param is None:
                continue
            param.setValue(value)

    def showEvent(self, event):
        self._capture_snapshot()
        super().showEvent(event)

    def done(self, result):
        if result != QDialog.Accepted:
            self._restore_snapshot()
        super().done(result)

