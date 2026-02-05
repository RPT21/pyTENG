from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import numpy as np
import time
import logging
import pandas as pd
import os

# ---------------- BUFFER PROCESSING THREAD ----------------
class BufferProcessor(QObject):
    process_buffer_signal = pyqtSignal(object)

    def __init__(self, fs, mainWindowReference, channel_config, task_name, parent=None):
        super().__init__(parent)
        self.fs = fs
        self.process_buffer_signal.connect(self.save_data)
        self.mainWindow = mainWindowReference
        self.local_path = self.mainWindow.local_path
        self.isSaving = False
        self.channel_config = channel_config
        self.task_name = task_name
        self.file_handle = None

        # Create a list of names and a list of indices
        self.channel_names = list(self.channel_config.keys())
        self.channel_indices = [self.channel_config[k][-1] for k in self.channel_names]

    @pyqtSlot(object)
    def save_data(self, data):

        # Initialize the saving process
        self.isSaving = True

        # Try to save the data into the disk
        try:
            data.tofile(self.file_handle)
        except Exception as e:
            print("Error saving data: ", e)
            self.mainWindow.automatic_mode = False
            self.mainWindow.stop_for_error = True
            self.mainWindow.trigger_adquisition_signal.emit()
        else:
            logging.info(f"{self.task_name} -> [+] Saved {len(data)} samples")

        # The data has been saved or an error has occurred
        self.isSaving = False

    def close_file(self):
        self.file_handle.close()
        print(f"File DAQ_{self.task_name}.bin has been closed")

    def open_file(self):
        self.file_handle = open(f"{self.local_path[0]}/DAQ_{self.task_name}.bin", 'ab')

    def Binary_to_Pickle(self):
        """This function converts the numpy binary file to pandas dataframe and saves it as pickle file."""
        file_path = f"{self.local_path[0]}/DAQ_{self.task_name}.bin"

        print(f"\nConverting DAQ_{self.task_name}.bin to Pickle ...")

        # Read the saved data
        raw_data = np.fromfile(file_path, dtype=np.float64)

        # Reshape the array
        data = raw_data.reshape(-1, len(self.channel_indices))

        # Create the timestamps
        t = np.arange(data.shape[0]) / self.fs

        # Create the dataframe
        df = pd.DataFrame(data, columns=self.channel_names)
        df.insert(0, "Time (s)", t)  # Insert time at the start

        # Save the dataframe
        rawdata_dir = os.path.dirname(self.local_path[0])
        filename = f'DAQ-{self.task_name}-{self.mainWindow.exp_id}.pkl'
        df.to_pickle(os.path.join(rawdata_dir, filename))

        print("Data saved to location:", os.path.join(rawdata_dir, filename))

        return filename

