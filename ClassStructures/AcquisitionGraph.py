import pyqtgraph as pg
import numpy as np
from PyQt5.QtGui import QFont

class AcquisitionGraph(pg.PlotWidget):
    def __init__(self, parent=None):
        super(AcquisitionGraph, self).__init__(parent)

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


    def _update_DAQ_Plot_Buffer(self, *args):
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
                self.plot_widget.setYRange(-10, 10)
            except Exception:
                pass
            self.plot_widget.setLabel('left', 'Amplitude', units='V', color='#e5e7eb', size='11pt', autoSIPrefix=False)
        else:
            # Digital: values 0 or 1, not voltage
            try:
                self.plot_widget.setYRange(0, 1)
            except Exception:
                pass
            self.plot_widget.setLabel('left', 'Digital signal', units='', color='#e5e7eb', size='11pt', autoSIPrefix=False)

        # Disconnect the plotter from the screen
        self.actual_plotter = None

        # Reshape the display_data buffer
        if self.display_data.size != DAQ_Task_Reference.PLOT_BUFFER_SIZE:
            self.display_data = np.empty(DAQ_Task_Reference.PLOT_BUFFER_SIZE, dtype=np.float64)

        # Calculate the array index corresponding to the selected signal
        self.index_pointer = selected[-1]

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
        time_axis = np.linspace(0, self.TimeWindowLength, plot_buffer_size)
        self.curve.setData(time_axis, self.display_data)