import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel)
from measurement_data_logger import DataLogger
from MeasurementGUI import MeasurementGUI
from MeasurementThread import MeasurementThread
from InstrumentManager import InstrumentManager

class MeasurementApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.data_logger = DataLogger()
        self.data_logger.init_plot()

        # Asserting that the data_logger has a 'fig' attribute.
        assert hasattr(self.data_logger, 'fig'), "DataLogger does not have the 'fig' attribute!"
        self.gui = MeasurementGUI(self.start_measurement, self.stop_program, self.data_logger)
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
        # 传递新的地址参数给我们在第一步中修改过的 InstrumentManager
        self.instrument_manager.connect_instruments(inst1_ip, inst2_ip, heater_addr, dc1_addr, dc2_addr)
        # [新增] 初始化直流源 (给温度计供电，例如 10uA)
        current_dc_val = 0.00001  # 10uA
        self.instrument_manager.setup_dc_sources(current_val=current_dc_val)
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

