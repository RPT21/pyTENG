import pyvisa

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
        }
        if normalized not in sense_to_query:
            raise ValueError("sense must be one of: VOLT, CURR, RES")

        raw_value = self._instrument.query(sense_to_query[normalized]).strip()
        return float(raw_value)

    @staticmethod
    def conversion_factor_from_range(measurement_range):
        """Map Keithley range to conversion factor.

        Current behavior is identity: conversion_factor = range.
        """
        return float(measurement_range)

    def get_conversion_factor_from_keithley(self, sense="VOLT"):
        """Convenience method used by DAQ channel conversion-mode logic."""
        return self.conversion_factor_from_range(self.read_range(sense=sense))
