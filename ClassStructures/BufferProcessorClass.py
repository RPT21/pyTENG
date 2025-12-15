from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import numpy as np
import time
import logging
import pandas as pd

# ---------------- BUFFER PROCESSING THREAD ----------------
class BufferProcessor(QObject):
    process_buffer_signal = pyqtSignal(object)

    def __init__(self, fs, mainWindowReference, channel_config, task_name, parent=None):
        super().__init__(parent)
        self.fs = fs
        self.process_buffer_signal.connect(self.save_data)
        self.timestamp = 0
        self.mainWindow = mainWindowReference
        self.local_path = self.mainWindow.local_path
        self.isSaving = False
        self.channel_config = channel_config
        self.task_name = task_name

    @pyqtSlot(object)
    def save_data(self, data):
        self.isSaving = True
        t = np.arange(data.shape[0]) / self.fs + self.timestamp
        self.timestamp = t[-1] + (t[1] - t[0])

        df = pd.DataFrame({"Time (s)": t})
        for channel_name in self.channel_config.keys():
            df[channel_name] = data[:, self.channel_config[channel_name][-1]]

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        df.to_pickle(f"{self.local_path[0]}/DAQ_{self.task_name}_{timestamp}.pkl")
        self.isSaving = False
        logging.info(f"{self.task_name} -> [+] Saved {len(data)} samples")