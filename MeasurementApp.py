import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel)
from measurement_data_logger import DataLogger
from MeasurementGUI import MeasurementGUI
from MeasurementThread import MeasurementThread
from InstrumentManager import InstrumentManager
from MultiPyVu import MultiVuClient as mvc

class MeasurementApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.data_logger = DataLogger()
        self.data_logger.init_plot()

        # Asserting that the data_logger has a 'fig' attribute.
        assert hasattr(self.data_logger, 'fig'), "DataLogger does not have the 'fig' attribute!"
        # Use a compatibility wrapper that accepts a `config` dict from the refactored GUI.
        self.gui = MeasurementGUI(self.start_measurement_from_config, self.stop_program, self.data_logger, self.set_temperature)
        #self.measurement_thread = MeasurementThread()
        self.instrument_manager = InstrumentManager()
        self.measurement_thread=None

    def _generate_amplitude_intervals(self, initial1, final1, step1, initial2, final2, step2, initial3, final3, step3,
                                      initial4, final4, step4):
        """Generates amplitude intervals."""
        intervals = [
            (initial1, final1, step1),
            (initial2, final2, step2),
            (initial3, final3, step3),
            (initial4, final4, step4)
        ]
        amplitude_values = np.array([])
        for start, end, step in intervals:
            interval_array = np.arange(start, end, step)
            amplitude_values = np.concatenate((amplitude_values, interval_array))
        return amplitude_values

    def generate_temp_list(self,initial_temp, final_temp, step_temp):
        current_temp = initial_temp
        temp_list = []
        if initial_temp > final_temp:
            while current_temp >= final_temp:
                temp_list.append(round(current_temp, 4))
                current_temp -= step_temp
        elif initial_temp < final_temp:
            while current_temp <= final_temp:
                temp_list.append(round(current_temp, 4))
                current_temp += step_temp
        return temp_list

    def start_measurement(self, host, port,inst1_ip, inst2_ip, heater_addr, dc1_addr, dc2_addr,
                          initial1_Amplitude,final1_Amplitude,step1_Amplitude,initial2_Amplitude,final2_Amplitude,step2_Amplitude,
                          initial3_Amplitude,final3_Amplitude,step3_Amplitude,initial4_Amplitude,final4_Amplitude,step4_Amplitude,
                          wait_time,temperature_changing,initial_temp,final_temp,step_temp,rate,frequency=17.777):
        # Re-initialize instruments every time before starting a measurement
        print("Host:", host)
        print("Port:", port)
        print("Instrument 1 IP:", inst1_ip)
        print("Instrument 2 IP:", inst2_ip)
        print("Heater Address (K6221):", heater_addr)
        print("DC Source 1 Address (K2400):", dc1_addr)
        print("DC Source 2 Address (K2400):", dc2_addr)
        temp_list = []
        #self.data_logger.init_plot()
        amplitude_values = self._generate_amplitude_intervals(initial1_Amplitude,final1_Amplitude,step1_Amplitude,initial2_Amplitude,final2_Amplitude,step2_Amplitude,initial3_Amplitude,final3_Amplitude,step3_Amplitude,initial4_Amplitude,final4_Amplitude,step4_Amplitude)
        # Set the save directory in the data logger
        save_directory = self.gui.folder_input.text() or "."  # Use current directory as default if no folder specified
        self.data_logger.set_save_directory(save_directory)
        # 在 MeasurementApp 的 start_measurement 方法中
        self.gui.update_amplitude_list(amplitude_values)
        # 传递新的地址参数给 InstrumentManager（依赖于当前测量模式）
        mode_key = 'fig1' if self.gui.mode_combo.currentText().startswith("Fig.1e") else 'fig2'
        self.instrument_manager.connect_instruments(inst1_ip, inst2_ip, heater_addr, dc1_addr, dc2_addr, mode=mode_key)

        # 仅在 Fig.1 模式下初始化并打开直流源 (用于 R vs T 的直流偏置)
        if mode_key == 'fig1':
            current_dc_val = 0.00001  # 10uA
            self.instrument_manager.setup_dc_sources(current_val=current_dc_val)
        else:
            current_dc_val = 0.0  # 不使用直流偏置
        # 从GUI获取temperature相关的设置
        # temperature_changing = self.gui.temp_changing_checkbox.isChecked()  # Assuming you used a QCheckBox for this
        # initial_temp = float(self.gui.initial_temp_input.text())
        # final_temp = float(self.gui.final_temp_input.text())
        # step_temp = float(self.gui.step_temp_input.text())
        if temperature_changing:
            temp_list = self.generate_temp_list(initial_temp, final_temp, step_temp) # Assuming you have this method in GUI
        # rate = float(self.gui.rate_input.text())  # Assuming you have an input for rate
        print(
            f"Starting measurement thread with Temperature Changing Parameters: Initial: {initial_temp}, Final: {final_temp}, Step: {step_temp}, Rate: {rate}")
        print(temp_list)
        # 创建MeasurementThread并传递所有必要的参数
        self.measurement_thread = MeasurementThread(
            self.gui,
            self.data_logger,
            host,
            port,
            self.instrument_manager.inst1,
            self.instrument_manager.inst2,
            self.instrument_manager.my_instrument_current,
            amplitude_values,
            wait_time,
            temperature_changing,
            temp_list,
            rate,
            current_dc_val,
            frequency
        )
        self.measurement_thread.measurementDone.connect(self.handle_measurement_done)
        self.measurement_thread.updatePlotSignal.connect(self.gui.refresh_plot)
        self.data_logger.updateTemperatureAmplitude.connect(self.gui.update_temperature_amplitude)
        self.measurement_thread.start()

    def set_temperature(self, ppms_config):
        """Set PPMS temperature without starting measurement."""
        host = ppms_config["host"]
        port = ppms_config["port"]
        target_T = ppms_config["target_T"]
        rate = ppms_config["rate"]
        tol = ppms_config["tol"]
        stable_sec = ppms_config["stable_sec"]
        timeout_min = ppms_config["timeout_min"]

        try:
            with mvc.MultiVuClient(host, port) as client:
                print(f"Setting temperature to {target_T} K at rate {rate} K/min")
                client.set_temperature(target_T, rate, client.temperature.approach_mode.no_overshoot)
                # Wait for stability (simple implementation)
                import time
                timeout = timeout_min * 60
                start_time = time.time()
                while time.time() - start_time < timeout:
                    T, sT = client.get_temperature()
                    if abs(T - target_T) < tol:
                        stable_count = 0
                        for _ in range(int(stable_sec)):
                            time.sleep(1)
                            T, sT = client.get_temperature()
                            if abs(T - target_T) < tol:
                                stable_count += 1
                            else:
                                stable_count = 0
                            if stable_count >= stable_sec:
                                print(f"Temperature stabilized at {T} K")
                                return
                    time.sleep(1)
                print("Temperature setting timeout")
        except Exception as e:
            print(f"Error setting temperature: {e}")

    def start_measurement_from_config(self, config):
        """Compatibility wrapper: starts a measurement using `config` dict from the refactored GUI.

        This maps the new GUI's config structure into the legacy measurement flow.
        """
        host = config["ppms"]["host"]
        port = config["ppms"]["port"]
        inst1_ip = config["lockins"]["lock1_ip"]
        inst2_ip = config["lockins"]["lock2_ip"]
        harm1 = config["lockins"].get("lock1_harm", 2)
        harm2 = config["lockins"].get("lock2_harm", 4)
        heater_addr = config["sources"]["lakeshore_ip"]
        dc1_addr = config["sources"]["dc1_addr"]
        dc2_addr = config["sources"]["dc2_addr"]
        amplitude_values = config["sweep"]["points"]
        wait_time = config["data"].get("wait_time", 70)
        temperature_changing = config["ppms"].get("enable", False)
        initial_temp = config["ppms"].get("target_T", 0.0)
        final_temp = initial_temp
        step_temp = 0
        rate = config["ppms"].get("rate", 1)
        frequency = config["sources"].get("heater_freq", 17.777)

        # Save directory (GUI overrides config if filled)
        save_directory = self.gui.folder_input.text() or config["data"].get("save_folder", ".")
        self.data_logger.set_save_directory(save_directory)

        # Try to update GUI amplitude list (compat API)
        try:
            self.gui.update_amplitude_list(amplitude_values)
        except Exception:
            pass

        # Connect instruments and setup DC sources depending on mode
        mode_key = config.get("mode_key", "fig1")
        self.instrument_manager.connect_instruments(inst1_ip, inst2_ip, heater_addr, dc1_addr, dc2_addr, mode=mode_key, harm1=harm1, harm2=harm2)

        if mode_key == 'fig1':
            current_dc_val = config["sources"].get("idc1", 1e-6)
            self.instrument_manager.setup_dc_sources(current_val=current_dc_val)
        else:
            # Fig.2 modes do not use DC sources
            current_dc_val = 0.0

        # Temperature plan
        temp_list = []
        if temperature_changing:
            temp_list = self.generate_temp_list(initial_temp, final_temp, step_temp)

        # Start measurement thread (similar to legacy method)
        self.measurement_thread = MeasurementThread(
            self.gui,
            self.data_logger,
            host,
            port,
            self.instrument_manager.inst1,
            self.instrument_manager.inst2,
            self.instrument_manager.my_instrument_current,
            amplitude_values,
            wait_time,
            temperature_changing,
            temp_list,
            rate,
            current_dc_val,
            frequency
        )
        self.measurement_thread.measurementDone.connect(self.handle_measurement_done)
        self.measurement_thread.updatePlotSignal.connect(self.gui.refresh_plot)
        self.data_logger.updateTemperatureAmplitude.connect(self.gui.update_temperature_amplitude)
        self.measurement_thread.start()

    def stop_program(self, event=None):
        if self.measurement_thread:
            self.measurement_thread.stop_requested=True
        self.gui.turn_off_indicator()
        self.gui.refresh_plot()

    def handle_measurement_done(self):
        self.gui.turn_off_indicator()

    def run(self):
        self.gui.show()
        sys.exit(self.app.exec_())

