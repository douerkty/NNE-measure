from lakeshore import PrecisionSource
import time

class LakeshoreController:
    def __init__(self, ip_address='10.16.87.186', voltage_limit=5, max_voltage=3):
        """
        初始化Lakeshore PrecisionSource并进行基本设置。

        参数:
            ip_address (str): 仪器的IP地址。
            voltage_limit (float): 设置的电压限制。
            max_voltage (float): 电流模式下的电压保护的最大值。
        """
        self.instrument = PrecisionSource(ip_address=ip_address)
        time.sleep(0.08)
        print(self.instrument.query('*IDN?'))
        time.sleep(0.08)
        self.instrument.reset_measurement_settings()
        time.sleep(0.08)
        self.instrument.route_terminals(output_connections_location='FRONT')
        time.sleep(0.08)
        self.instrument.set_voltage_limit(voltage_limit)
        time.sleep(0.08)
        self.instrument.set_current_mode_voltage_protection(max_voltage)
        time.sleep(0.08)
        self.instrument.disable_output()
        time.sleep(0.08)
        self.instrument.enable_autorange()
        time.sleep(0.08)

    def enable_output(self):
        """开启仪器输出。"""
        self.instrument.enable_output()
        print("Instrument output enabled.")

    def output_sine_current(self, amplitude, frequency, offset=0.0, phase=0.0):
        """
        输出正弦电流。

        参数:
            amplitude (float): 正弦电流的幅度。
            frequency (float): 正弦电流的频率。
            offset (float): 正弦电流的偏移。默认为0.0。
            phase (float): 正弦电流的相位。默认为0.0。
        """
        self.instrument.output_sine_current(amplitude, frequency, offset, phase)
        print(f"Sine current output set. Amplitude: {amplitude}, Frequency: {frequency}, Offset: {offset}, Phase: {phase}")
    def disable_output(self):
        """关闭仪器输出。"""
        self.instrument.disable_output()
        print("Instrument output disabled.")