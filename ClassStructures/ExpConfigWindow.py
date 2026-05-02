from PyQt5.QtWidgets import (QPushButton, QVBoxLayout,
                             QHBoxLayout, QDialog)

from pyqtgraph.parametertree import Parameter, ParameterTree

class ExpConfigWindow(QDialog):
    def __init__(self, METADATA_COLUMNS, parent=None):
        super().__init__(parent)

        # Build the hidden Parameter group (not shown until dialog opens)
        children = []
        for col, meta in METADATA_COLUMNS.items():
            if col in ('Date', 'ReadingTime (s)'):
                continue  # Auto-generated and must not be editable in the dialog.
            ptype = meta.get('type', 'str')
            if ptype not in ('str', 'int', 'float', 'bool', 'list'):
                ptype = 'str'
            children.append({'name': col, 'type': ptype, 'value': meta.get('default', '')})

        self.metadata_param_tree = Parameter.create(name='ExperimentDefaults', type='group', children=children)
        self.METADATA_COLUMNS = METADATA_COLUMNS

        # Backup current values
        orig = {}
        for col in list(METADATA_COLUMNS.keys()):
            if col in ('Date', 'ReadingTime (s)'):
                continue
            try:
                p = self.metadata_param_tree.param(col)
                orig[col] = p.value() if p is not None else None
            except Exception:
                orig[col] = None

        self.setWindowTitle("Edit Experiment Defaults")
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

        def on_cancel():
            # restore originals
            for col, val in orig.items():
                try:
                    p = self.metadata_param_tree.param(col)
                    if p is not None:
                        p.setValue(val)
                except Exception:
                    pass
            self.reject()

        def on_save():
            tribu_param = self.metadata_param_tree.param('TribuId')
            rload_param = self.metadata_param_tree.param('RloadId')

            if tribu_param is not None:
                self.tribu_id = tribu_param.value()
            else:
                self.tribu_id = None

            if rload_param is not None:
                self.rload_id = rload_param.value()
            else:
                self.rload_id = None

            self.accept()

        btn_cancel.clicked.connect(on_cancel)
        btn_save.clicked.connect(on_save)

