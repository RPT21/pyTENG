from ClassStructures.RaspberryInterface import RaspberryInterface
rb_hostname = "192.168.100.200"
rb_port = 22
rb_username = "TENG"
rb_password = "raspberry"
rb_remote_path = "/var/opt/codesys/PlcLogic/FTP_Folder"

raspberry = RaspberryInterface(hostname=rb_hostname,
                                port=rb_port,
                                username=rb_username,
                                password=rb_password)


raspberry.connect()

import tkinter as tk
from tkinter import filedialog

# Get file save location from user:
print("Please provide a save location and name for incoming data.")
root = tk.Tk()
root.withdraw()  # Amaga la finestra princial de tkinter
root.lift()   # Posa la finestra emergent en primer pla
root.attributes('-topmost', True)  # La finestra sempre al davant

fullFileName = filedialog.askdirectory()

if fullFileName:
    fullFileName = fullFileName.replace("/", "\\")
    raspberry.download_folder(rb_remote_path, local_path=fullFileName)
    raspberry.remove_files_with_extension(rb_remote_path)
else:
    print("Canceled")

