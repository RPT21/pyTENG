from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
import copy
import json

from PyDAQmx.DAQmxConstants import (
    DAQmx_Val_ChanForAllLines,
    DAQmx_Val_ContSamps,
    DAQmx_Val_Diff,
    DAQmx_Val_GroupByChannel,
    DAQmx_Val_GroupByScanNumber,
    DAQmx_Val_RSE,
    DAQmx_Val_Rising,
    DAQmx_Val_Volts,
)


PORT_CONFIG_OPTIONS = [
    ("None", None),
    ("DAQmx_Val_RSE", DAQmx_Val_RSE),
    ("DAQmx_Val_Diff", DAQmx_Val_Diff),
]
PORT_CONFIG_LABEL_BY_VALUE = {value: label for label, value in PORT_CONFIG_OPTIONS}
PORT_CONFIG_VALUE_BY_LABEL = {label: value for label, value in PORT_CONFIG_OPTIONS}


def _default_task(task_type="analog"):
    return {
        "NAME": "New Task",
        "SAMPLE_RATE": 10000,
        "DAQ_CHANNELS": {
            "Channel 1": {
                "port": "",
                "port_config": DAQmx_Val_Diff if task_type == "analog" else None,
                "conversion_source": "none",
                "conversion_factor": None,
            }
        },
        "TRIGGER_SOURCE": None,
        "TYPE": task_type,
    }


class DAQProfilesWindow(QDialog):
    def __init__(self, DAQ_PROFILES, main_window_reference):
        super().__init__(main_window_reference)

        self.main_window = main_window_reference
        self.daq_profiles = DAQ_PROFILES
        self._suspend_refresh = False
        self._current_profile_name = None
        self._current_task_index = 0
        self._task_editor_dirty = False

        self.setWindowTitle("Edit DAQ Profiles")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fb;
            }
            QLabel {
                color: #1f2937;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox, QLineEdit, QSpinBox {
                padding: 6px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: white;
                color: #1f2937;
                font-size: 11px;
            }
            QTableWidget {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: white;
                color: #1f2937;
                gridline-color: #e5e7eb;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #e5e7eb;
                color: #111827;
                padding: 5px;
                border: 0px;
                font-weight: 600;
                font-size: 11px;
            }
            QGroupBox {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 12px;
                font-weight: 600;
                color: #374151;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QPushButton {
                padding: 8px 14px;
                border-radius: 4px;
                border: none;
                font-weight: 600;
                font-size: 11px;
                min-height: 32px;
            }
            QPushButton#primaryAction {
                background-color: #2563eb;
                color: white;
            }
            QPushButton#primaryAction:hover {
                background-color: #1d4ed8;
            }
            QPushButton#dangerAction {
                background-color: #dc2626;
                color: white;
            }
            QPushButton#dangerAction:hover {
                background-color: #b91c1c;
            }
            QPushButton#secondaryAction {
                background-color: #6b7280;
                color: white;
            }
            QPushButton#secondaryAction:hover {
                background-color: #4b5563;
            }
        """)

        self._build_ui()
        self._refresh_profile_combo(select_name=self._initial_profile_name())

    def _build_ui(self):
        dlg_layout = QVBoxLayout(self)
        dlg_layout.setContentsMargins(16, 16, 16, 16)
        dlg_layout.setSpacing(12)

        help_label = QLabel("Create, duplicate, edit, save, and load DAQ task profiles.")
        help_label.setStyleSheet("color: #6b7280; font-size: 12px; font-weight: 500;")
        dlg_layout.addWidget(help_label)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_row.addWidget(self.profile_combo, 1)

        self.btn_new_profile = QPushButton("New Profile")
        self.btn_duplicate_profile = QPushButton("Duplicate Profile")
        self.btn_rename_profile = QPushButton("Rename Profile")
        self.btn_delete_profile = QPushButton("Delete Profile")
        self.btn_export_profiles = QPushButton("Save Profiles")
        self.btn_import_profiles = QPushButton("Load Profiles")

        for btn in (self.btn_new_profile, self.btn_duplicate_profile, self.btn_rename_profile, self.btn_delete_profile,
                    self.btn_export_profiles, self.btn_import_profiles):
            btn.setObjectName("primaryAction")
            profile_row.addWidget(btn)

        dlg_layout.addLayout(profile_row)

        self.btn_new_profile.clicked.connect(self._on_new_profile)
        self.btn_duplicate_profile.clicked.connect(self._on_duplicate_profile)
        self.btn_rename_profile.clicked.connect(self._on_rename_profile)
        self.btn_delete_profile.clicked.connect(self._on_delete_profile)
        self.btn_export_profiles.clicked.connect(self._export_profiles_to_file)
        self.btn_import_profiles.clicked.connect(self._import_profiles_from_file)

        task_box = QGroupBox("Task configuration")
        task_layout = QVBoxLayout(task_box)
        task_layout.setContentsMargins(12, 18, 12, 12)
        task_layout.setSpacing(10)

        task_top_row = QHBoxLayout()
        task_top_row.addWidget(QLabel("Task:"))
        self.task_combo = QComboBox()
        self.task_combo.currentIndexChanged.connect(self._on_task_changed)
        task_top_row.addWidget(self.task_combo, 1)

        self.btn_add_task = QPushButton("Add Task")
        self.btn_duplicate_task = QPushButton("Duplicate Task")
        self.btn_delete_task = QPushButton("Delete Task")
        for btn in (self.btn_add_task, self.btn_duplicate_task, self.btn_delete_task):
            btn.setObjectName("primaryAction" if btn != self.btn_delete_task else "dangerAction")
            task_top_row.addWidget(btn)
        task_layout.addLayout(task_top_row)

        self.btn_add_task.clicked.connect(self._on_add_task)
        self.btn_duplicate_task.clicked.connect(self._on_duplicate_task)
        self.btn_delete_task.clicked.connect(self._on_delete_task)

        form_group = QGroupBox("Selected task details")
        form_layout = QFormLayout(form_group)
        form_layout.setContentsMargins(12, 18, 12, 12)
        form_layout.setSpacing(8)

        self.task_name_edit = QLineEdit()
        self.task_name_edit.textEdited.connect(self._on_task_name_edited)
        self.task_name_edit.editingFinished.connect(self._commit_editor_state)
        form_layout.addRow("Task name", self.task_name_edit)

        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(1, 10_000_000)
        self.sample_rate_spin.setSingleStep(100)
        self.sample_rate_spin.valueChanged.connect(self._commit_editor_state)
        form_layout.addRow("Sample rate (Hz)", self.sample_rate_spin)

        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems(["analog", "digital"])
        self.task_type_combo.currentTextChanged.connect(self._on_task_type_changed)
        form_layout.addRow("Type", self.task_type_combo)

        # Trigger source selector: allow common choices and a custom entry
        self.trigger_source_combo = QComboBox()
        self.trigger_source_combo.addItems(["None", "PFI0", "PFI1", "Custom..."])
        self.trigger_source_combo.currentTextChanged.connect(self._on_trigger_source_changed)

        self.trigger_source_custom = QLineEdit()
        self.trigger_source_custom.setPlaceholderText("Enter custom trigger (e.g. PFI2)")
        # mark editor dirty when custom text edited and commit on finish
        self.trigger_source_custom.textEdited.connect(self._mark_task_editor_dirty)
        self.trigger_source_custom.editingFinished.connect(self._commit_editor_state)
        self.trigger_source_custom.setVisible(False)

        trigger_layout = QHBoxLayout()
        trigger_layout.addWidget(self.trigger_source_combo)
        trigger_layout.addWidget(self.trigger_source_custom)
        form_layout.addRow("Trigger source", trigger_layout)

        task_layout.addWidget(form_group)

        channel_group = QGroupBox("DAQ channels")
        channel_layout = QVBoxLayout(channel_group)
        channel_layout.setContentsMargins(12, 18, 12, 12)
        channel_layout.setSpacing(8)

        channel_button_row = QHBoxLayout()
        self.btn_add_channel = QPushButton("Add Channel")
        self.btn_remove_channel = QPushButton("Remove Channel")
        self.btn_add_channel.setObjectName("primaryAction")
        self.btn_remove_channel.setObjectName("dangerAction")
        self.btn_add_channel.clicked.connect(self._on_add_channel)
        self.btn_remove_channel.clicked.connect(self._on_remove_channel)
        channel_button_row.addWidget(self.btn_add_channel)
        channel_button_row.addWidget(self.btn_remove_channel)
        channel_button_row.addStretch(1)
        channel_layout.addLayout(channel_button_row)

        self.channel_table = QTableWidget(0, 5)
        self.channel_table.setHorizontalHeaderLabels([
            "Channel name",
            "Port",
            "Port config",
            "Conversion source",
            "Conversion factor",
        ])
        self.channel_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.channel_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.channel_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.channel_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.channel_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.channel_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.channel_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        channel_layout.addWidget(self.channel_table)

        task_layout.addWidget(channel_group)

        dlg_layout.addWidget(task_box, 1)

        action_row = QHBoxLayout()
        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 12px; font-weight: 500;")
        action_row.addWidget(self.status_label, 1)

        self.btn_save_profile = QPushButton("Save Profile")
        self.btn_apply_active = QPushButton("Apply Active")
        self.btn_cancel = QPushButton("Close")
        self.btn_save_profile.setObjectName("primaryAction")
        self.btn_apply_active.setObjectName("primaryAction")
        self.btn_cancel.setObjectName("secondaryAction")
        self.btn_save_profile.clicked.connect(self._on_save_profile)
        self.btn_apply_active.clicked.connect(self._on_apply_active)
        self.btn_cancel.clicked.connect(self.reject)
        action_row.addWidget(self.btn_save_profile)
        action_row.addWidget(self.btn_apply_active)
        action_row.addWidget(self.btn_cancel)
        dlg_layout.addLayout(action_row)

    def _initial_profile_name(self):
        active_name = self.main_window.active_daq_profile_name
        if active_name in self.daq_profiles:
            return active_name
        return next(iter(self.daq_profiles.keys()), "")

    def _current_profile_tasks(self, profile_name=None):
        if profile_name is None:
            profile_name = self.profile_combo.currentText().strip()
        return self.daq_profiles.setdefault(profile_name, [])

    def _port_config_to_label(self, value):
        return PORT_CONFIG_LABEL_BY_VALUE.get(value, "None")

    def _port_config_from_label(self, label):
        return PORT_CONFIG_VALUE_BY_LABEL.get(label, None)

    def _serialize_task_for_file(self, task):
        serialized = copy.deepcopy(task)
        serialized.pop("DAQ_TASK_REFERENCE", None)
        for channel in serialized.get("DAQ_CHANNELS", {}).values():
            if isinstance(channel, dict):
                channel["port_config"] = self._port_config_to_label(channel.get("port_config"))
        return serialized

    def _deserialize_task_from_file(self, task):
        deserialized = copy.deepcopy(task)
        for channel in deserialized.get("DAQ_CHANNELS", {}).values():
            if isinstance(channel, dict):
                channel["port_config"] = self._port_config_from_label(channel.get("port_config"))
        return deserialized

    def _profile_payload(self):
        return {
            "profiles": {
                name: [self._serialize_task_for_file(task) for task in tasks]
                for name, tasks in self.daq_profiles.items()
            }
        }

    def _load_profile_payload(self, payload):
        if isinstance(payload, dict) and "profiles" in payload and isinstance(payload["profiles"], dict):
            profiles = payload["profiles"]
        elif isinstance(payload, dict):
            profiles = payload
        else:
            raise ValueError("Profile file must contain a mapping of profile names to task lists.")

        normalized = {}
        for profile_name, tasks in profiles.items():
            normalized[profile_name] = [self._deserialize_task_from_file(task) for task in tasks]
            self._validate_daq_tasks(normalized[profile_name])
        return normalized

    def _refresh_profile_combo(self, select_name=None):
        self._suspend_refresh = True
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(list(self.daq_profiles.keys()))
        if select_name and select_name in self.daq_profiles:
            self.profile_combo.setCurrentText(select_name)
        elif self.profile_combo.count() > 0:
            self.profile_combo.setCurrentIndex(0)
        self.profile_combo.blockSignals(False)
        self._suspend_refresh = False
        self._load_selected_profile(self.profile_combo.currentText().strip())

    def _load_selected_profile(self, profile_name):
        if not profile_name:
            return
        tasks = self.daq_profiles.get(profile_name, [])
        if not tasks:
            tasks = [_default_task()]
            self.daq_profiles[profile_name] = tasks

        self._current_profile_name = profile_name
        self._suspend_refresh = True
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        for task in tasks:
            self.task_combo.addItem(str(task.get("NAME", "Unnamed task")))
        self.task_combo.setCurrentIndex(0)
        self.task_combo.blockSignals(False)
        self._suspend_refresh = False
        self._load_task_into_editor(0)
        self._update_status(f"Editing profile '{profile_name}'.")

    def _load_task_into_editor(self, task_index):
        tasks = self._current_profile_tasks()
        if not tasks:
            task_index = 0
            tasks.append(_default_task())

        task_index = max(0, min(task_index, len(tasks) - 1))
        self._current_task_index = task_index
        task = tasks[task_index]

        self._suspend_refresh = True
        self.task_name_edit.setText(str(task.get("NAME", "")))
        self.sample_rate_spin.setValue(int(task.get("SAMPLE_RATE", 10000)))
        self.task_type_combo.setCurrentText(str(task.get("TYPE", "analog")))
        trigger_source = task.get("TRIGGER_SOURCE", None)
        # Populate trigger selector
        if trigger_source is None or trigger_source == "":
            self.trigger_source_combo.setCurrentText("None")
            self.trigger_source_custom.setVisible(False)
            self.trigger_source_custom.setText("")
        elif trigger_source in ("PFI0", "PFI1"):
            self.trigger_source_combo.setCurrentText(trigger_source)
            self.trigger_source_custom.setVisible(False)
            self.trigger_source_custom.setText("")
        else:
            self.trigger_source_combo.setCurrentText("Custom...")
            self.trigger_source_custom.setVisible(True)
            self.trigger_source_custom.setText(str(trigger_source))
        self._populate_channel_table(task.get("DAQ_CHANNELS", {}))
        self._suspend_refresh = False
        self._clear_task_editor_dirty()
        self._update_task_combo_labels()

    def _update_task_combo_labels(self):
        tasks = self._current_profile_tasks()
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        for task in tasks:
            self.task_combo.addItem(str(task.get("NAME", "Unnamed task")))
        self.task_combo.setCurrentIndex(min(self._current_task_index, max(self.task_combo.count() - 1, 0)))
        self.task_combo.blockSignals(False)

    def _mark_task_editor_dirty(self):
        if not self._suspend_refresh:
            self._task_editor_dirty = True

    def _clear_task_editor_dirty(self):
        self._task_editor_dirty = False

    def _on_task_name_edited(self, text):
        if self._suspend_refresh:
            return
        self._mark_task_editor_dirty()
        if 0 <= self._current_task_index < self.task_combo.count():
            self.task_combo.setItemText(self._current_task_index, text.strip() or "")

    def _populate_channel_table(self, channels):
        self.channel_table.setRowCount(0)
        for channel_name, channel_config in channels.items():
            self._append_channel_row(channel_name, channel_config)
        if self.channel_table.rowCount() == 0:
            self._append_channel_row("Channel 1", {
                "port": "",
                "port_config": DAQmx_Val_Diff if self.task_type_combo.currentText() == "analog" else None,
                "conversion_source": "none",
                "conversion_factor": None,
            })

    def _normalized_conversion_source_label(self, channel_config):
        source = str(channel_config.get("conversion_source", "")).strip().lower()
        conversion = channel_config.get("conversion_factor", None)

        # Backward compatibility: infer source when old profiles only store conversion_factor.
        if source not in ("none", "custom", "keithley"):
            if conversion in (None, ""):
                source = "none"
            elif isinstance(conversion, (int, float)):
                source = "custom"
            elif isinstance(conversion, str) and conversion.strip().lower() in ("keithley", "keithley_range"):
                source = "keithley"
            else:
                source = "custom"

        return {"none": "None", "custom": "Custom", "keithley": "Keithley"}[source]

    def _row_for_cell_widget(self, widget, column_index):
        for row in range(self.channel_table.rowCount()):
            if self.channel_table.cellWidget(row, column_index) is widget:
                return row
        return -1

    def _on_conversion_source_changed(self, _):
        if self._suspend_refresh:
            return

        source_combo = self.sender()
        if not isinstance(source_combo, QComboBox):
            return

        row = self._row_for_cell_widget(source_combo, 3)
        if row < 0:
            return

        conversion_item = self.channel_table.item(row, 4)
        if conversion_item is None:
            conversion_item = QTableWidgetItem("")
            self.channel_table.setItem(row, 4, conversion_item)

        source_label = source_combo.currentText()
        if source_label == "None":
            conversion_item.setText("")
        elif source_label == "Keithley":
            # Display hint in the editable cell; parser ignores this cell for Keithley mode.
            conversion_item.setText("range from Keithley")
        elif source_label == "Custom" and conversion_item.text().strip().lower() == "range from keithley":
            conversion_item.setText("")

        self._mark_task_editor_dirty()

    def _append_channel_row(self, channel_name="Channel 1", channel_config=None):
        channel_config = channel_config or {}
        row = self.channel_table.rowCount()
        self.channel_table.insertRow(row)

        name_item = QTableWidgetItem(str(channel_name))
        port_item = QTableWidgetItem(str(channel_config.get("port", "")))
        conversion_source_label = self._normalized_conversion_source_label(channel_config)
        conversion = channel_config.get("conversion_factor", None)
        if conversion_source_label == "None":
            conversion_text = ""
        elif conversion_source_label == "Keithley":
            conversion_text = "range from Keithley"
        else:
            conversion_text = "" if conversion in (None, "") else str(conversion)
        conversion_item = QTableWidgetItem(conversion_text)

        self.channel_table.setItem(row, 0, name_item)
        self.channel_table.setItem(row, 1, port_item)
        self.channel_table.setItem(row, 4, conversion_item)

        port_combo = QComboBox()
        for label, value in PORT_CONFIG_OPTIONS:
            port_combo.addItem(label, value)
        port_combo.setCurrentText(self._port_config_to_label(channel_config.get("port_config", None)))
        self.channel_table.setCellWidget(row, 2, port_combo)

        conversion_source_combo = QComboBox()
        conversion_source_combo.addItems(["None", "Custom", "Keithley"])
        conversion_source_combo.setCurrentText(conversion_source_label)
        conversion_source_combo.currentTextChanged.connect(self._on_conversion_source_changed)
        self.channel_table.setCellWidget(row, 3, conversion_source_combo)

    def _task_from_editor(self):
        task_name = self.task_name_edit.text().strip()
        if not task_name:
            raise ValueError("Task name cannot be empty.")

        sample_rate = int(self.sample_rate_spin.value())
        if sample_rate <= 0:
            raise ValueError("Sample rate must be greater than zero.")

        task_type = self.task_type_combo.currentText().strip()
        if task_type not in ("analog", "digital"):
            raise ValueError("Task type must be 'analog' or 'digital'.")

        # Read trigger source from selector/custom
        combo_val = self.trigger_source_combo.currentText()
        if combo_val == "None":
            trigger_source = None
        elif combo_val == "Custom...":
            txt = self.trigger_source_custom.text().strip()
            trigger_source = txt if txt else None
        else:
            trigger_source = combo_val

        channels = {}
        for row in range(self.channel_table.rowCount()):
            name_item = self.channel_table.item(row, 0)
            port_item = self.channel_table.item(row, 1)
            conversion_item = self.channel_table.item(row, 4)
            port_combo = self.channel_table.cellWidget(row, 2)
            conversion_source_combo = self.channel_table.cellWidget(row, 3)

            channel_name = name_item.text().strip() if name_item else ""
            port = port_item.text().strip() if port_item else ""
            port_config = port_combo.currentData() if isinstance(port_combo, QComboBox) else None
            conversion_text = conversion_item.text().strip() if conversion_item else ""
            conversion_source_label = conversion_source_combo.currentText() if isinstance(conversion_source_combo, QComboBox) else "None"

            if not channel_name:
                continue
            if not port:
                raise ValueError(f"Channel '{channel_name}' requires a port.")
            if channel_name in channels:
                raise ValueError(f"Duplicate channel name '{channel_name}' in the same task.")

            if conversion_source_label == "None":
                conversion_source = "none"
                conversion_factor = None
            elif conversion_source_label == "Keithley":
                conversion_source = "keithley"
                conversion_factor = None
            else:
                conversion_source = "custom"
                if not conversion_text:
                    raise ValueError(f"Channel '{channel_name}' requires a custom conversion factor value.")
                try:
                    conversion_factor = float(conversion_text)
                except ValueError as exc:
                    raise ValueError(f"Channel '{channel_name}' has an invalid conversion factor.") from exc

            channels[channel_name] = {
                "port": port,
                "port_config": port_config,
                "conversion_source": conversion_source,
                "conversion_factor": conversion_factor,
            }

        if not channels:
            raise ValueError("Each task must contain at least one channel.")

        return {
            "NAME": task_name,
            "SAMPLE_RATE": sample_rate,
            "DAQ_CHANNELS": channels,
            "TRIGGER_SOURCE": trigger_source,
            "TYPE": task_type,
        }

    def _commit_current_task(self, profile_name=None):
        if profile_name is None:
            profile_name = self.profile_combo.currentText().strip()
        if not profile_name:
            return
        tasks = self._current_profile_tasks(profile_name=profile_name)
        if not tasks:
            tasks.append(_default_task())

        edited_task = self._task_from_editor()
        self._validate_daq_tasks([edited_task])
        tasks[self._current_task_index] = edited_task
        self._clear_task_editor_dirty()

        # Refresh task names only for the profile that is currently selected in UI.
        if profile_name == self.profile_combo.currentText().strip():
            self._update_task_combo_labels()

    def _validate_daq_tasks(self, tasks):
        if not isinstance(tasks, list) or not tasks:
            raise ValueError("DAQ profile must be a non-empty list of task dictionaries.")

        seen_names = set()
        for idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                raise ValueError(f"Task #{idx + 1} must be a dictionary.")

            for key in ("NAME", "SAMPLE_RATE", "DAQ_CHANNELS", "TYPE"):
                if key not in task:
                    raise ValueError(f"Task #{idx + 1} is missing required key '{key}'.")

            task_name = str(task["NAME"]).strip()
            if not task_name:
                raise ValueError(f"Task #{idx + 1} must have a non-empty NAME.")
            if task_name in seen_names:
                raise ValueError(f"Task name '{task_name}' is duplicated within the profile.")
            seen_names.add(task_name)

            sample_rate = task["SAMPLE_RATE"]
            if not isinstance(sample_rate, int) or sample_rate <= 0:
                raise ValueError(f"Task '{task_name}' must have a positive integer SAMPLE_RATE.")

            if task["TYPE"] not in ("analog", "digital"):
                raise ValueError(f"Task '{task_name}' has invalid TYPE '{task['TYPE']}'.")

            channels = task["DAQ_CHANNELS"]
            if not isinstance(channels, dict) or not channels:
                raise ValueError(f"Task '{task_name}' must contain at least one DAQ channel.")

            for channel_name, channel in channels.items():
                if not isinstance(channel, dict):
                    raise ValueError(f"Channel '{channel_name}' in task '{task_name}' must be a dictionary.")
                if not str(channel.get("port", "")).strip():
                    raise ValueError(f"Channel '{channel_name}' in task '{task_name}' must define a port.")
                if channel.get("port_config", None) not in PORT_CONFIG_LABEL_BY_VALUE and channel.get("port_config", None) not in (None,):
                    raise ValueError(f"Channel '{channel_name}' in task '{task_name}' has an unsupported port_config value.")

                conversion_source = str(channel.get("conversion_source", "")).strip().lower()
                conversion_factor = channel.get("conversion_factor", None)
                if conversion_source not in ("", "none", "custom", "keithley"):
                    raise ValueError(
                        f"Channel '{channel_name}' in task '{task_name}' has invalid conversion_source '{conversion_source}'."
                    )

                # Backward compatibility when conversion_source is not present.
                if conversion_source == "":
                    if conversion_factor in (None, ""):
                        conversion_source = "none"
                    elif isinstance(conversion_factor, str) and conversion_factor.strip().lower() in ("keithley", "keithley_range"):
                        conversion_source = "keithley"
                    else:
                        conversion_source = "custom"

                if conversion_source == "custom":
                    if conversion_factor in (None, ""):
                        raise ValueError(
                            f"Channel '{channel_name}' in task '{task_name}' needs a numeric conversion_factor for custom mode."
                        )
                    if not isinstance(conversion_factor, (int, float)):
                        raise ValueError(
                            f"Channel '{channel_name}' in task '{task_name}' has non-numeric conversion_factor for custom mode."
                        )
                elif conversion_source in ("none", "keithley"):
                    if conversion_factor not in (None, ""):
                        raise ValueError(
                            f"Channel '{channel_name}' in task '{task_name}' must not define conversion_factor when conversion_source is '{conversion_source}'."
                        )

    def _update_status(self, text):
        self.status_label.setText(text)

    def _editor_has_unsaved_changes(self, profile_name=None):
        if profile_name is None:
            profile_name = self._current_profile_name

        if not profile_name or profile_name not in self.daq_profiles:
            return False

        tasks = self.daq_profiles.get(profile_name, [])
        if not tasks or not (0 <= self._current_task_index < len(tasks)):
            return False

        if self._task_editor_dirty:
            return True

        try:
            return self._task_from_editor() != tasks[self._current_task_index]
        except Exception:
            return True

    def _prompt_unsaved_changes_before_profile_switch(self, previous_profile_name, next_profile_name):
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Unsaved changes")
        dialog.setText(f"You have unsaved changes in profile '{previous_profile_name}'.")
        dialog.setInformativeText(f"Do you want to save the changes before switching to '{next_profile_name}'?")
        dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        dialog.setDefaultButton(QMessageBox.Save)
        return dialog.exec_()

    def _prompt_unsaved_changes_before_close(self):
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Unsaved changes")
        dialog.setText("You have unsaved changes in the current task.")
        dialog.setInformativeText("Do you want to save the changes before closing the profile editor?")
        dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        dialog.setDefaultButton(QMessageBox.Save)
        return dialog.exec_()

    def _close_with_unsaved_changes_prompt(self):
        previous_profile_name = self._current_profile_name
        if previous_profile_name and self._editor_has_unsaved_changes(previous_profile_name):
            reply = self._prompt_unsaved_changes_before_close()

            if reply == QMessageBox.Cancel:
                return False

            if reply == QMessageBox.Save:
                try:
                    self._commit_current_task(profile_name=previous_profile_name)
                except Exception as exc:
                    QMessageBox.warning(self, "DAQ profiles", str(exc))
                    return False

        return True

    def _set_profile_combo_without_signal(self, profile_name):
        self._suspend_refresh = True
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentText(profile_name or "")
        self.profile_combo.blockSignals(False)
        self._suspend_refresh = False

    def _on_profile_changed(self, profile_name):
        if self._suspend_refresh or not profile_name:
            return
        previous_profile_name = self._current_profile_name

        if previous_profile_name and self._editor_has_unsaved_changes(previous_profile_name):
            reply = self._prompt_unsaved_changes_before_profile_switch(previous_profile_name, profile_name)

            if reply == QMessageBox.Cancel:
                self._set_profile_combo_without_signal(previous_profile_name)
                return

            if reply == QMessageBox.Save:
                try:
                    self._commit_current_task(profile_name=previous_profile_name)
                except Exception as exc:
                    QMessageBox.warning(self, "DAQ profiles", str(exc))
                    self._set_profile_combo_without_signal(previous_profile_name)
                    return

        try:
            previous_tasks = self.daq_profiles.get(previous_profile_name, []) if previous_profile_name else []
            can_commit_previous_task = (
                bool(previous_profile_name)
                and bool(previous_tasks)
                and 0 <= self._current_task_index < len(previous_tasks)
            )
            if can_commit_previous_task and not self._editor_has_unsaved_changes(previous_profile_name):
                self._commit_current_task(profile_name=previous_profile_name)
        except Exception as exc:
            QMessageBox.warning(self, "DAQ profiles", str(exc))
            self._set_profile_combo_without_signal(previous_profile_name)
            return
        self._load_selected_profile(profile_name)

    def _on_task_changed(self, index):
        if self._suspend_refresh:
            return
        try:
            self._commit_current_task()
        except Exception as exc:
            QMessageBox.warning(self, "DAQ profiles", str(exc))
            self._suspend_refresh = True
            self.task_combo.blockSignals(True)
            self.task_combo.setCurrentIndex(self._current_task_index)
            self.task_combo.blockSignals(False)
            self._suspend_refresh = False
            return
        self._load_task_into_editor(index)

    def _on_task_type_changed(self, _):
        if self._suspend_refresh:
            return
        self._commit_editor_state()
        task = self._task_from_editor()
        channels = task.get("DAQ_CHANNELS", {}) if isinstance(task, dict) else {}
        self._populate_channel_table(channels if isinstance(channels, dict) else {})

    def _on_trigger_source_changed(self, text):
        # Show/hide custom field and mark editor dirty when user changes selection
        if self._suspend_refresh:
            return
        if text == "Custom...":
            self.trigger_source_custom.setVisible(True)
        else:
            self.trigger_source_custom.setVisible(False)
        self._mark_task_editor_dirty()

    def _commit_editor_state(self):
        self._mark_task_editor_dirty()

    def _on_add_task(self):
        try:
            self._commit_current_task()
        except Exception as exc:
            QMessageBox.warning(self, "DAQ profiles", str(exc))
            return

        task_type = self.task_type_combo.currentText().strip() or "analog"
        new_task = _default_task(task_type=task_type)
        new_task["NAME"] = self._unique_task_name("New Task")
        self._current_profile_tasks().append(new_task)
        self._load_task_into_editor(len(self._current_profile_tasks()) - 1)

    def _on_duplicate_task(self):
        try:
            self._commit_current_task()
        except Exception as exc:
            QMessageBox.warning(self, "DAQ profiles", str(exc))
            return

        tasks = self._current_profile_tasks()
        if not tasks:
            return
        duplicated = copy.deepcopy(tasks[self._current_task_index])
        duplicated["NAME"] = self._unique_task_name(f"{duplicated.get('NAME', 'Task')} Copy")
        tasks.append(duplicated)
        self._load_task_into_editor(len(tasks) - 1)

    def _on_delete_task(self):
        tasks = self._current_profile_tasks()
        if len(tasks) <= 1:
            QMessageBox.warning(self, "DAQ profiles", "At least one task must remain in a profile.")
            return
        reply = QMessageBox.question(
            self,
            "Delete DAQ task",
            f"Delete task '{tasks[self._current_task_index].get('NAME', 'Unnamed task')}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        tasks.pop(self._current_task_index)
        self._load_task_into_editor(max(0, self._current_task_index - 1))

    def _on_new_profile(self):
        name, ok = QInputDialog.getText(self, "New DAQ profile", "Profile name:")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.daq_profiles:
            QMessageBox.warning(self, "DAQ profiles", f"Profile '{name}' already exists.")
            return
        # New profiles start from a clean default task schema.
        self.daq_profiles[name] = [copy.deepcopy(_default_task())]
        self._refresh_profile_combo(select_name=name)

    def _on_duplicate_profile(self):
        name, ok = QInputDialog.getText(self, "Duplicate DAQ profile", "New profile name:")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.daq_profiles:
            QMessageBox.warning(self, "DAQ profiles", f"Profile '{name}' already exists.")
            return
        current_name = self.profile_combo.currentText().strip() or self._initial_profile_name()
        self.daq_profiles[name] = copy.deepcopy(self.daq_profiles[current_name])
        self._refresh_profile_combo(select_name=name)

    def _on_rename_profile(self):
        current_name = self.profile_combo.currentText().strip()
        if not current_name:
            return
        name, ok = QInputDialog.getText(self, "Rename DAQ profile", "New profile name:", text=current_name)
        name = name.strip()
        if not ok or not name or name == current_name:
            return
        if name in self.daq_profiles:
            QMessageBox.warning(self, "DAQ profiles", f"Profile '{name}' already exists.")
            return

        self.daq_profiles[name] = self.daq_profiles.pop(current_name)
        if self.main_window is not None and getattr(self.main_window, "active_daq_profile_name", None) == current_name:
            self.main_window.active_daq_profile_name = name
            if hasattr(self.main_window, "_sync_active_profile_label"):
                self.main_window._sync_active_profile_label()
        self._refresh_profile_combo(select_name=name)

    def _on_delete_profile(self):
        if len(self.daq_profiles) <= 1:
            QMessageBox.warning(self, "DAQ profiles", "At least one profile must remain.")
            return

        current_name = self.profile_combo.currentText().strip()
        if not current_name:
            return
        if self.main_window is not None and getattr(self.main_window, "active_daq_profile_name", None) == current_name:
            QMessageBox.warning(self, "DAQ profiles", "Activate another profile before deleting the active one.")
            return

        reply = QMessageBox.question(
            self,
            "Delete DAQ profile",
            f"Delete profile '{current_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.daq_profiles.pop(current_name, None)
        self._refresh_profile_combo(select_name=next(iter(self.daq_profiles.keys())))

    def _on_save_profile(self):
        try:
            self._commit_current_task()
            self._validate_daq_tasks(self._current_profile_tasks())
            self._update_status(f"Profile '{self.profile_combo.currentText().strip()}' saved in memory.")
            QMessageBox.information(self, "DAQ profiles", "Profile saved.")
        except Exception as exc:
            QMessageBox.critical(self, "DAQ profiles", f"Could not save profile: {exc}")

    def _on_apply_active(self):
        try:
            self._commit_current_task()
            self._validate_daq_tasks(self._current_profile_tasks())
            profile_name = self.profile_combo.currentText().strip()
            if not profile_name:
                raise ValueError("No profile selected.")
            if self.main_window is None:
                raise RuntimeError("No parent window is available to apply the profile.")
            self.main_window.active_daq_profile_name = profile_name
            if hasattr(self.main_window, "_sync_active_profile_label"):
                self.main_window._sync_active_profile_label()
            self.main_window.apply_daq_profile(profile_name)
            self._update_status(f"Profile '{profile_name}' applied to runtime.")
            QMessageBox.information(self, "DAQ profiles", f"Profile '{profile_name}' applied.")
        except Exception as exc:
            QMessageBox.critical(self, "DAQ profiles", str(exc))

    def _export_profiles_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save DAQ profiles",
            "daq_profiles.json",
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                json.dump(self._profile_payload(), handle, indent=2, ensure_ascii=False)
            self._update_status(f"Profiles saved to {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "DAQ profiles", f"Could not save profiles: {exc}")

    def _import_profiles_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load DAQ profiles",
            "",
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            loaded_profiles = self._load_profile_payload(payload)
            self.daq_profiles.clear()
            self.daq_profiles.update(loaded_profiles)

            if self.main_window is not None and getattr(self.main_window, "active_daq_profile_name", None) not in self.daq_profiles:
                self.main_window.active_daq_profile_name = next(iter(self.daq_profiles.keys()))
                if hasattr(self.main_window, "_sync_active_profile_label"):
                    self.main_window._sync_active_profile_label()

            self._refresh_profile_combo(select_name=next(iter(self.daq_profiles.keys())))
            self._update_status(f"Profiles loaded from {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "DAQ profiles", f"Could not load profiles: {exc}")

    def _unique_task_name(self, base_name):
        existing = {task.get("NAME", "") for task in self._current_profile_tasks()}
        if base_name not in existing:
            return base_name
        counter = 2
        while f"{base_name} {counter}" in existing:
            counter += 1
        return f"{base_name} {counter}"

    def _on_add_channel(self):
        self._append_channel_row(self._unique_channel_name("Channel"), {
            "port": "",
            "port_config": DAQmx_Val_Diff if self.task_type_combo.currentText() == "analog" else None,
            "conversion_source": "none",
            "conversion_factor": None,
        })
        self._commit_editor_state()

    def _on_remove_channel(self):
        selected_rows = sorted({index.row() for index in self.channel_table.selectedIndexes()}, reverse=True)
        if not selected_rows:
            selected_rows = [self.channel_table.rowCount() - 1] if self.channel_table.rowCount() > 0 else []
        for row in selected_rows:
            if 0 <= row < self.channel_table.rowCount():
                self.channel_table.removeRow(row)
        if self.channel_table.rowCount() == 0:
            self._append_channel_row(self._unique_channel_name("Channel"), {
                "port": "",
                "port_config": DAQmx_Val_Diff if self.task_type_combo.currentText() == "analog" else None,
                "conversion_source": "none",
                "conversion_factor": None,
            })
        self._commit_editor_state()

    def _unique_channel_name(self, base_name):
        existing = set()
        for row in range(self.channel_table.rowCount()):
            item = self.channel_table.item(row, 0)
            if item is not None:
                existing.add(item.text().strip())
        if base_name not in existing:
            return base_name
        counter = 2
        while f"{base_name} {counter}" in existing:
            counter += 1
        return f"{base_name} {counter}"

    def _sync_active_profile_label(self):
        if self.main_window is not None and hasattr(self.main_window, "daq_profile_label"):
            self.main_window.daq_profile_label.setText(f"Active DAQ profile: {self.main_window.active_daq_profile_name}")

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_profile_combo(select_name=self._initial_profile_name())

    def closeEvent(self, event):
        if self._close_with_unsaved_changes_prompt():
            event.accept()
        else:
            event.ignore()

    def reject(self):
        self.close()

