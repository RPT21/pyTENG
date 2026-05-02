import pyqtgraph as pg
import numpy as np
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QComboBox

class ChannelSelectorComboBox(QComboBox):

    def __init__(self, DAQ_TASKS, AcquisitionGraphReference):
        super().__init__()

        # Generate a dictionary with all channels and corresponding tasks
        self.ALL_CHANNELS = {}
        for n, task in enumerate(DAQ_TASKS):
            for channel_name, channel_value in task["DAQ_CHANNELS"].items():
                self.ALL_CHANNELS[f"{task['NAME']} - {channel_name}"] = [channel_value[-1], task["DAQ_TASK_REFERENCE"]]

        # Create the channel display list
        self._populate_signal_selector(self.ALL_CHANNELS)
        self.setToolTip("Select the channel to display")

        # Connect with the Acquisition Graph
        self.AcquisitionGraphReference = AcquisitionGraphReference
        self.currentIndexChanged.connect(AcquisitionGraphReference.update_DAQ_Plot_Buffer)
        self.AcquisitionGraphReference.signal_selector = self

    def value(self):
        return self.currentData()

    def _populate_signal_selector(self, total_tasks, preferred_label=None):
        current_label = preferred_label or self.currentText()
        self.blockSignals(True)
        self.clear()

        for label, channel_value in total_tasks.items():
            self.addItem(label, channel_value)

        if current_label:
            idx = self.findText(current_label)
            if idx >= 0:
                self.setCurrentIndex(idx)
            elif self.count() > 0:
                self.setCurrentIndex(0)
        elif self.count() > 0:
            self.setCurrentIndex(0)

        self.blockSignals(False)

class AcquisitionGraph(pg.PlotWidget):
    def __init__(self, TimeWindowLength, parent=None):
        super(AcquisitionGraph, self).__init__(parent)

        self.TimeWindowLength = TimeWindowLength
        self.signal_selector = None

        self.setLabel('left', 'Amplitude', units='V', color='#e5e7eb', size='11pt', autoSIPrefix=False)
        self.setLabel('bottom', 'Time', units='s', color='#e5e7eb', size='11pt', autoSIPrefix=False)
        self.curve = self.plot([], pen=pg.mkPen('#fbbf24', width=2.5))
        self.display_data = np.array([], dtype=np.float64)
        self.setBackground("#111827")
        self.showGrid(x=True, y=True, alpha=0.35)
        self.getAxis('left').setPen(pg.mkPen('#64748b', width=1.5))
        self.getAxis('left').setTextPen(pg.mkPen('#cbd5e1'))
        axis_font = QFont('Segoe UI', 11)
        axis_font.setWeight(QFont.Medium)
        self.getAxis('left').setStyle(tickFont=axis_font)
        self.setMinimumHeight(420)

        # Set initial axis ranges: Y-axis from -10 to 10V, X-axis from 0 to TimeWindowLength
        self.setYRange(-10, 10)
        self.setXRange(0, self.TimeWindowLength)


    def update_DAQ_Plot_Buffer(self, *args):
        selected = self.signal_selector.value()
        if not selected:
            self.actual_plotter = None
            self.index_pointer = None
            self.curve.setData([])
            return

        # Obtain the DAQ Task Reference
        DAQ_Task_Reference = selected[1]

        # Adjust axis and labels depending on task/channel type
        task_type = getattr(DAQ_Task_Reference, 'task_type', None)
        if task_type == 'analog':
            # Analog: voltage between -10 and 10
            try:
                self.setYRange(-10, 10)
            except Exception:
                pass
            self.setLabel('left', 'Amplitude', units='V', color='#e5e7eb', size='11pt', autoSIPrefix=False)
        else:
            # Digital: values 0 or 1, not voltage
            try:
                self.setYRange(0, 1)
            except Exception:
                pass
            self.setLabel('left', 'Digital signal', units='', color='#e5e7eb', size='11pt', autoSIPrefix=False)

        # Disconnect the plotter from the screen
        self.actual_plotter = None

        # Reshape the display_data buffer
        if self.display_data.size != DAQ_Task_Reference.PLOT_BUFFER_SIZE:
            self.display_data = np.empty(DAQ_Task_Reference.PLOT_BUFFER_SIZE, dtype=np.float64)

        # Calculate the array index corresponding to the selected signal
        self.index_pointer = selected[0]

        # Select the actual plotter
        self.actual_plotter = DAQ_Task_Reference

    def flush_screen(self):
        self.actual_plotter = None
        self.curve.setData([])

    def update_plot(self):
        if self.actual_plotter is None:
            return
        if self.display_data.size == 0:
            return

        plot_buffer = self.actual_plotter.plot_buffer
        plot_buffer_size = self.actual_plotter.PLOT_BUFFER_SIZE
        write_index = self.actual_plotter.write_index

        tail_size = plot_buffer_size - write_index
        self.display_data[:tail_size] = plot_buffer[write_index:, self.index_pointer]
        self.display_data[tail_size:] = plot_buffer[:write_index, self.index_pointer]

        # Create time axis from 0 to TimeWindowLength
        time_axis = np.linspace(0, self.TimeWindowLength, plot_buffer_size)  # S'ha de modificar que no es crei cada vegada, sino que es mantingui i només s'actualitzi si el plot_buffer_size canvia
        self.curve.setData(time_axis, self.display_data)