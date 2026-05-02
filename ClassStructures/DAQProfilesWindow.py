from PyQt5.QtWidgets import (QPushButton, QVBoxLayout,
                             QLabel, QHBoxLayout, QInputDialog, QDialog,
                             QComboBox, QPlainTextEdit, QMessageBox)
import copy
import json

class DAQProfilesWindow(QDialog):

    def __init__(self, DAQ_PROFILES, parent=None):

        super().__init__(parent)

        """Open a modal dialog to edit, create and apply DAQ profiles."""
        self.daq_profiles = DAQ_PROFILES

        self.setWindowTitle("Edit DAQ Profiles")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fb;
            }
            QLabel {
                color: #1f2937;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox {
                padding: 6px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: white;
                color: #1f2937;
                font-size: 11px;
            }
            QPlainTextEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: white;
                color: #1f2937;
                font-family: 'Courier New';
                font-size: 10px;
                padding: 4px;
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

        dlg_layout = QVBoxLayout(self)
        dlg_layout.setContentsMargins(16, 16, 16, 16)
        dlg_layout.setSpacing(12)

        help_label = QLabel("Edit the selected profile as JSON, then Save or Apply Active.")
        help_label.setStyleSheet("color: #6b7280; font-size: 12px; font-weight: 500;")
        dlg_layout.addWidget(help_label)

        profile_combo = QComboBox()
        profile_combo.addItems(list(self.daq_profiles.keys()))
        dlg_layout.addWidget(profile_combo)

        profile_editor = QPlainTextEdit()
        profile_editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        dlg_layout.addWidget(profile_editor)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        btn_new = QPushButton("New")
        btn_duplicate = QPushButton("Duplicate")
        btn_rename = QPushButton("Rename")
        btn_delete = QPushButton("Delete")
        btn_save = QPushButton("Save")
        btn_apply = QPushButton("Apply Active")
        btn_cancel = QPushButton("Cancel")

        btn_new.setObjectName("primaryAction")
        btn_duplicate.setObjectName("primaryAction")
        btn_rename.setObjectName("primaryAction")
        btn_delete.setObjectName("dangerAction")
        btn_save.setObjectName("primaryAction")
        btn_apply.setObjectName("primaryAction")
        btn_cancel.setObjectName("secondaryAction")

        for btn in (btn_new, btn_duplicate, btn_rename, btn_delete, btn_save, btn_apply, btn_cancel):
            btn.setMinimumWidth(80)
            button_row.addWidget(btn)
        dlg_layout.addLayout(button_row)

        def load_profile(name):
            profile_editor.setPlainText(self._serialize_daq_tasks(self.daq_profiles[name]))

        def selected_profile_name():
            return profile_combo.currentText().strip()

        def refresh_combo(select_name=None):
            profile_combo.blockSignals(True)
            profile_combo.clear()
            profile_combo.addItems(list(self.daq_profiles.keys()))
            if select_name and select_name in self.daq_profiles:
                profile_combo.setCurrentText(select_name)
            profile_combo.blockSignals(False)
            load_profile(profile_combo.currentText())

        def store_current_editor_to_profile(profile_name):
            tasks = self._deserialize_daq_tasks(profile_editor.toPlainText())
            self.daq_profiles[profile_name] = tasks

        def on_profile_changed():
            load_profile(selected_profile_name())

        def on_new():
            name, ok = QInputDialog.getText(self, "New DAQ profile", "Profile name:")
            name = name.strip()
            if not ok or not name:
                return
            if name in self.daq_profiles:
                QMessageBox.warning(self, "DAQ profiles", f"Profile '{name}' already exists.")
                return
            current_name = selected_profile_name()
            self.daq_profiles[name] = copy.deepcopy(self.daq_profiles[current_name])
            refresh_combo(name)

        def on_duplicate():
            name, ok = QInputDialog.getText(self, "Duplicate DAQ profile", "New profile name:")
            name = name.strip()
            if not ok or not name:
                return
            if name in self.daq_profiles:
                QMessageBox.warning(self, "DAQ profiles", f"Profile '{name}' already exists.")
                return
            current_name = selected_profile_name()
            self.daq_profiles[name] = copy.deepcopy(self.daq_profiles[current_name])
            refresh_combo(name)

        def on_rename():
            current_name = selected_profile_name()
            name, ok = QInputDialog.getText(self, "Rename DAQ profile", "New profile name:", text=current_name)
            name = name.strip()
            if not ok or not name or name == current_name:
                return
            if name in self.daq_profiles:
                QMessageBox.warning(self, "DAQ profiles", f"Profile '{name}' already exists.")
                return
            self.daq_profiles[name] = self.daq_profiles.pop(current_name)
            if current_name == self.active_daq_profile_name:
                self.active_daq_profile_name = name
                self._sync_active_profile_label()
            refresh_combo(name)

        def on_delete():
            if len(self.daq_profiles) <= 1:
                QMessageBox.warning(self, "DAQ profiles", "At least one profile must remain.")
                return
            current_name = selected_profile_name()
            if current_name == self.active_daq_profile_name:
                QMessageBox.warning(self, "DAQ profiles", "Activate another profile before deleting the active one.")
                return
            reply = QMessageBox.question(self, "Delete DAQ profile",
                                         f"Delete profile '{current_name}'?",
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            self.daq_profiles.pop(current_name, None)
            refresh_combo(next(iter(self.daq_profiles.keys())))

        def on_save():
            try:
                store_current_editor_to_profile(selected_profile_name())
                QMessageBox.information(self, "DAQ profiles", "Profile saved.")
            except Exception as exc:
                QMessageBox.critical(self, "DAQ profiles", f"Could not save profile: {exc}")

        def on_apply_active():
            try:
                profile_name = selected_profile_name()
                store_current_editor_to_profile(profile_name)
                self._rebuild_daq_runtime_from_profile(profile_name)
                QMessageBox.information(self, "DAQ profiles", f"Profile '{profile_name}' applied.")
            except Exception as exc:
                QMessageBox.critical(self, "DAQ profiles", str(exc))

        profile_combo.currentTextChanged.connect(lambda _: on_profile_changed())
        btn_new.clicked.connect(on_new)
        btn_duplicate.clicked.connect(on_duplicate)
        btn_rename.clicked.connect(on_rename)
        btn_delete.clicked.connect(on_delete)
        btn_save.clicked.connect(on_save)
        btn_apply.clicked.connect(on_apply_active)
        btn_cancel.clicked.connect(self.reject)

        load_profile(profile_combo.currentText())

    def _sync_active_profile_label(self):
        self.daq_profile_label.setText(f"Active DAQ profile: {self.active_daq_profile_name}")

    def _serialize_daq_tasks(self, daq_tasks):
        return json.dumps(daq_tasks, indent=2, ensure_ascii=False, default=str)

    def _deserialize_daq_tasks(self, text):
        tasks = json.loads(text)
        self._validate_daq_tasks(tasks)
        return tasks

    def _validate_daq_tasks(self, tasks):
        if not isinstance(tasks, list) or not tasks:
            raise ValueError("DAQ profile must be a non-empty list of task dictionaries.")

        for idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                raise ValueError(f"Task #{idx + 1} must be a dictionary.")

            for key in ("NAME", "SAMPLE_RATE", "DAQ_CHANNELS", "TYPE"):
                if key not in task:
                    raise ValueError(f"Task #{idx + 1} is missing required key '{key}'.")

            if not isinstance(task["DAQ_CHANNELS"], dict) or not task["DAQ_CHANNELS"]:
                raise ValueError(f"Task #{idx + 1} must contain at least one DAQ channel.")

            if task["TYPE"] not in ("analog", "digital"):
                raise ValueError(f"Task #{idx + 1} has invalid TYPE '{task['TYPE']}'.")

    def _close_runtime_daq_resources(self):
        self.actual_plotter = None
        self.index_pointer = None
        try:
            self.curve.setData([])
        except Exception:
            pass

        dev_comunicator = getattr(self, "dev_comunicator", None)

        for task in getattr(dev_comunicator, "AcquisitionTasks", []):
            try:
                task.StopTask()
            except Exception:
                pass
            try:
                task.ClearTask()
            except Exception:
                pass

        for attr_name in (
            "DO_task_LinMotTrigger",
            "DO_task_RelayCode",
            "DO_task_PrepareRaspberry",
            "DI_task_Raspberry_status_0",
            "DI_task_Raspberry_status_1",
        ):
            task = getattr(dev_comunicator, attr_name, None)
            if task is None:
                continue
            try:
                if attr_name == "DO_task_RelayCode":
                    task.set_lines([0, 0, 0, 0, 0, 0])
                elif attr_name == "DO_task_LinMotTrigger":
                    task.set_line(0)
                elif attr_name == "DO_task_PrepareRaspberry":
                    task.set_line(0)
            except Exception:
                pass
            try:
                task.StopTask()
            except Exception:
                pass
            try:
                task.ClearTask()
            except Exception:
                pass

        for processor in getattr(self, "buffer_processors", []):
            try:
                if processor.file_handle is not None and not processor.file_handle.closed:
                    processor.close_file()
            except Exception:
                pass

        for thread in getattr(self, "thread_savers", []):
            try:
                thread.quit()
                thread.wait()
            except Exception:
                pass

        if hasattr(self, "thread_communicator"):
            try:
                self.thread_communicator.quit()
                self.thread_communicator.wait()
            except Exception:
                pass

    def _rebuild_daq_runtime_from_profile(self, profile_name):
        if profile_name not in self.daq_profiles:
            raise KeyError(f"Unknown DAQ profile '{profile_name}'.")

        if self.moveLinMot[0]:
            raise RuntimeError("Stop the acquisition before applying a new DAQ profile.")

        profile_tasks = copy.deepcopy(self.daq_profiles[profile_name])

        self.DAQ_TASKS_METADATA = copy.deepcopy(profile_tasks)

        # Preserve the original channel dictionaries for metadata and expose indexed
        # channels to the runtime objects, as the current acquisition stack expects.
        for task in profile_tasks:
            for idx, (name, config) in enumerate(task["DAQ_CHANNELS"].items()):
                task["DAQ_CHANNELS"][name] = [config, idx]

        # Stop and clear the current runtime DAQ stack.
        self._close_runtime_daq_resources()

        # Rebuild acquisition parameters and the runtime task list.
        self.ACQUISITION_PARAMS = {}
        for task in profile_tasks:
            internal_buffer_size = _get_daq_internal_buffer_size(task["SAMPLE_RATE"])
            initial_samples_per_callback = int(task["SAMPLE_RATE"] / self.DAQ_USB_TRANSFER_FREQUENCY)
            divisors_of_internal_buffer = _find_divisors(internal_buffer_size)
            samples_per_callback = min(divisors_of_internal_buffer,
                                      key=lambda x: abs(x - initial_samples_per_callback))

            if samples_per_callback != initial_samples_per_callback:
                print(f"Task {task['NAME']}: Adjusted SAMPLES_PER_CALLBACK from {initial_samples_per_callback} to {samples_per_callback}")
                print(f"  Task sampling rate: {task['SAMPLE_RATE']} Hz, DAQ Internal buffer size: {internal_buffer_size}")

            callbacks_per_buffer = int(self.BUFFER_SAVING_TIME_INTERVAL * self.DAQ_USB_TRANSFER_FREQUENCY)
            plot_buffer_size = ((task["SAMPLE_RATE"] * self.TimeWindowLength) // samples_per_callback) * samples_per_callback

            self.ACQUISITION_PARAMS[task["NAME"]] = {
                'SAMPLES_PER_CALLBACK': samples_per_callback,
                'BUFFER_SIZE': samples_per_callback * callbacks_per_buffer,
                'PLOT_BUFFER_SIZE': plot_buffer_size,
                'INTERNAL_BUFFER_SIZE': internal_buffer_size,
            }

        self.DAQ_TASKS = profile_tasks

        self.buffer_processors = []
        self.thread_savers = []
        self.task_names = []
        for n, task in enumerate(self.DAQ_TASKS):
            self.buffer_processors.append(BufferProcessor(fs=task["SAMPLE_RATE"],
                                                          mainWindowReference=self,
                                                          channel_config=task["DAQ_CHANNELS"],
                                                          task_name=task["NAME"],
                                                          task_type=task["TYPE"]))
            self.thread_savers.append(QThread())
            self.task_names.append(task["NAME"])
            self.buffer_processors[n].moveToThread(self.thread_savers[n])
            self.thread_savers[n].start()

        self.dev_comunicator = DeviceCommunicator(mainWindowReference=self,
                                                  RelayCodeTask=self.RelayCodeTask,
                                                  LinMotTriggerTask=self.LinMotTriggerTask,
                                                  LinMotTriggerLine=self.LinMotTriggerLine,
                                                  PrepareRaspberryLine=self.PrepareRaspberryLine,
                                                  RaspberryStatus_0_Line=self.RaspberryStatus_0_Line,
                                                  RaspberryStatus_1_Line=self.RaspberryStatus_1_Line,
                                                  RelayCodeLines=self.RelayCodeLines)

        self.thread_communicator = QThread()
        self.dev_comunicator.moveToThread(self.thread_communicator)
        self.thread_communicator.start()

        total_tasks = {}
        for n, task in enumerate(self.DAQ_TASKS):
            for channel in task["DAQ_CHANNELS"].keys():
                task["DAQ_CHANNELS"][channel].insert(-1, self.dev_comunicator.AcquisitionTasks[n])
            for channel_name, channel_value in task["DAQ_CHANNELS"].items():
                total_tasks[f"{task['NAME']} - {channel_name}"] = channel_value

        previous_label = self.signal_selector.currentText() if hasattr(self, "signal_selector") else None
        self._populate_signal_selector(total_tasks, preferred_label=previous_label)

        for task in self.dev_comunicator.AcquisitionTasks:
            task.data_column_selector = self.signal_selector

        self.active_daq_profile_name = profile_name
        self._sync_active_profile_label()
        self._update_DAQ_Plot_Buffer()
