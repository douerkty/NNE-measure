import time
from PyQt5.QtCore import QThread, pyqtSignal
from MultiPyVu import MultiVuClient as mvc

class MeasurementThread(QThread):
    measurementDone = pyqtSignal()  # Signal to notify when measurement is complete
    updatePlotSignal = pyqtSignal()  # New signal, used to request graphical updates

    def __init__(self, gui, data_logger, host, port, inst1,
                 inst2, my_instrument_current,amplitude_values,wait_time,temperature_changing,temp_list,rate,current_dc_val,frequency=17.777):
        super().__init__()
        self.gui = gui
        self.data_logger = data_logger
        self.inst1 = inst1
        self.inst2 = inst2
        self.current_dc_val = current_dc_val
        self.my_instrument_current = my_instrument_current
        self.amplitude_values = amplitude_values
        print(amplitude_values)
        self.host = host
        self.port = port
        self.measurement_thread = None
        self.stop_requested=False
        self.wait_time=wait_time
        self.temperature_changing=temperature_changing
        print(temperature_changing)
        self.temp_list = temp_list
        self.rate = rate
        self.frequency = frequency
    
    def _measure_for_amplitude(self, amplitude):
        try:
            print("begin")
            self.my_instrument_current.output_sine_current(amplitude, self.frequency)
            time.sleep(5)
            self.my_instrument_current.enable_output()
            time.sleep(self.wait_time)  # Reduced sleep time for better responsiveness
        except Exception as e:
            print(f"Error during measurement for amplitude {amplitude}: {e}")

    def _update_data(self, count,amplitude):
        try:
            if count % 10 == 0:
                self.inst1.set_automatic_acgain()
                time.sleep(10)
                self.inst2.set_automatic_acgain()
                time.sleep(10)
                self.inst1.set_sensitivity1(max_attempts=26)
                self.inst2.set_sensitivity1(max_attempts=26)
                self.inst1.set_sensitivity2(max_attempts=26)
                self.inst2.set_sensitivity2(max_attempts=26)
                #self.inst1.disable_automatic_acgain()
                self.inst1.optimize_acgain()
                time.sleep(10)
                #self.inst2.disable_automatic_acgain()
                self.inst2.optimize_acgain()
                time.sleep(60)
                self.inst1.set_sensitivity2(max_attempts=22)
                self.inst2.set_sensitivity2(max_attempts=22)
            # Update data in data_logger (safe to do in worker thread)
            self.data_logger.update_measurements(self.inst1, self.inst2, amplitude, self.host, self.port,self.current_dc_val)
            # Request GUI thread to update/refresh plot via signal
            self.updatePlotSignal.emit()
            # Save data (can remain in worker thread; consider moving to background if slow)
            self.data_logger.save_data_to_txt()
        except Exception as e:
            print(f"Error updating data: {e}")

    def run(self):
        #self._setup_instruments()
        #amplitude_values = self.generate_amplitude_intervals()
        print(self.temperature_changing)
        print(self.temp_list)
        if self.temperature_changing:
            for temp in self.temp_list:
                print(f"Setting temperature to: {temp}")
                with mvc.MultiVuClient(self.host, self.port) as client:
                    time.sleep(5)
                    temperature_set=temp
                    print(f"prepare set temperature: {temperature_set}")
                    client.set_temperature(temperature_set,
                                           self.rate,
                                           client.temperature.approach_mode.no_overshoot)
                    time.sleep(100)
                count = 0
                for amplitude in self.amplitude_values:
                    if self.stop_requested:
                        break
                    self._measure_for_amplitude(amplitude)
                    self._update_data(count, amplitude)
                    count += 1
                    if count == 10:
                        count = 0
                self.my_instrument_current.disable_output()
                self.measurementDone.emit()
        else:
            count = 0
            print("without temperature control")
            for amplitude in self.amplitude_values:
                if self.stop_requested:
                    break
                self._measure_for_amplitude(amplitude)
                self._update_data(count, amplitude)
                count += 1
                if count == 10:
                    count = 0
            self.my_instrument_current.disable_output()
            self.measurementDone.emit()



    def get_amplitude_values(self):
        return self.amplitude_values

    def request_stop(self):
        self.stop_requested = True
