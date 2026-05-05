import pyvisa
import time

class KeithleyInterface:
    """Minimal Keithley helper to read the active measurement range.

    The conversion factor used by DAQ channels can be derived from the instrument
    range (identity mapping by default).
    """

    def __init__(self, resource_name=None, visa_backend=""):
        self.resource_name = resource_name
        self.visa_backend = visa_backend
        self._resource_manager = None
        self._instrument = None

    def connect(self, resource_name=None, timeout_ms=5000):
        """Connect to the Keithley using PyVISA.
        Raises:
            ValueError: if no resource name is provided.
        """
        if resource_name:
            self.resource_name = resource_name
        if not self.resource_name:
            raise ValueError("A Keithley VISA resource name is required (e.g. 'USB0::...::INSTR').")

        self._resource_manager = pyvisa.ResourceManager(self.visa_backend)
        self._instrument = self._resource_manager.open_resource(self.resource_name)
        self._instrument.timeout = int(timeout_ms)
        return self._instrument.query("*IDN?").strip()

    def disconnect(self):
        if self._instrument is not None:
            self._instrument.close()
            self._instrument = None
        if self._resource_manager is not None:
            self._resource_manager.close()
            self._resource_manager = None

    def _require_connection(self):
        if self._instrument is None:
            raise RuntimeError("Keithley is not connected. Call connect() first.")

    def read_range(self, sense="VOLT"):
        """Read the active range from the Keithley for a given sense type.

        Supported values: VOLT, CURR, RES.
        """
        self._require_connection()

        normalized = str(sense).strip().upper()
        sense_to_query = {
            "VOLT": "SENS:VOLT:RANG?",
            "CURR": "SENS:CURR:RANG?",
            "RES": "SENS:RES:RANG?",
            "CHAR": "SENS:CHAR:RANG?",
        }
        if normalized not in sense_to_query:
            raise ValueError("sense must be one of: VOLT, CURR, RES")

        raw_value = self._instrument.query(sense_to_query[normalized]).strip()
        return float(raw_value)

    @staticmethod
    def conversion_factor_from_range(measurement_range):
        """Map Keithley range to conversion factor."""
        conversion_factor = measurement_range / 2
        return conversion_factor

    def get_conversion_factor_from_keithley(self, sense="VOLT"):
        """Convenience method used by DAQ channel conversion-mode logic."""
        return self.conversion_factor_from_range(self.read_range(sense=sense))

    def send_ren_line(self, command, wait_time=0.1):
        """Send a command to the Keithley REN Control Bus Line."""
        self._require_connection()
        self._instrument.control_ren(command)
        time.sleep(wait_time)

    def send(self, command, wait_time=0.1):
        """Send a command to the Keithley SCPI Bus."""
        self._require_connection()
        self._instrument.write(command)
        time.sleep(wait_time)

    def query(self, command, wait_time=0.1):
        """Query a command to the Keithley SCPI Bus."""
        self._require_connection()
        data = self._instrument.query(command).strip()
        time.sleep(wait_time)
        return data

    def wait_for_srq(self):
        """Wait until status byte (bit 6) is active (SRQ)"""
        while True:
            try:
                stb = self._instrument.stb  # Status Byte
                if stb & 64:
                    return
            except Exception:
                continue
            time.sleep(0.2)

    def set_manual_control(self, wait_time=0.1):
        self._require_connection()
        self._instrument.write(":SYST:LOC")
        time.sleep(wait_time)

    def set_remote_control(self, wait_time=0.1):
        self._require_connection()
        self._instrument.write(":SYST:REM")
        time.sleep(wait_time)


if __name__ == "__main__":
    keithley = KeithleyInterface(resource_name="GPIB0::14::INSTR")
    print("Device id:", keithley.connect())
    print("Keithley range:", keithley.read_range(sense="VOLT"))
    print("Conversion factor:", keithley.get_conversion_factor_from_keithley())
    keithley.set_manual_control()
    keithley.disconnect()