# 文件名: keithley_drivers.py
import pyvisa
import time

class Keithley6221_ACSource:
    """
    用于控制 Keithley 6221 交流电流源 (对应论文中的加热器 Heater 电源)。
    论文参数: Sine wave, Frequency = 17.777 Hz.
    """
    def __init__(self, resource_name):
        """
        参数:
            resource_name (str): VISA 地址, 例如 'GPIB0::12::INSTR'
        """
        self.rm = pyvisa.ResourceManager()
        try:
            self.inst = self.rm.open_resource(resource_name)
            print(f"已连接 Keithley 6221: {self.inst.query('*IDN?')}")
            self.inst.write('*RST') # 复位
            time.sleep(1)
        except Exception as e:
            print(f"连接 Keithley 6221 失败: {e}")

    def setup_sine_wave(self, frequency=17.777, amplitude=0):
        """配置输出波形为正弦波，并设置频率和初始幅度"""
        try:
            self.inst.write('SOUR:WAVE:FUNC SIN')      # 设置为正弦波
            self.inst.write(f'SOUR:WAVE:FREQ {frequency}') # 设置频率 (论文: 17.777 Hz)
            self.inst.write(f'SOUR:WAVE:AMPL {amplitude}') # 设置幅度 (单位: Amp)
            self.inst.write('SOUR:WAVE:PMAR:STAT ON')  # 开启相位标记 (用于触发锁相放大器)
            self.inst.write('SOUR:WAVE:PMAR:OLIN 1')   # 输出触发信号到 Trigger Link 1
            print(f"Keithley 6221 configured: Sine, {frequency}Hz, {amplitude}A")
        except Exception as e:
            print(f"配置波形失败: {e}")

    def set_amplitude(self, amplitude):
        """更新电流幅度 (用于扫描电流 I_h)"""
        self.inst.write(f'SOUR:WAVE:AMPL {amplitude}')

    def enable_output(self):
        """开启输出 (Arm and Start)"""
        self.inst.write('SOUR:WAVE:ARM')
        self.inst.write('SOUR:WAVE:INIT')
        print("Keithley 6221 Output ENABLED")

    def disable_output(self):
        """关闭输出"""
        self.inst.write('SOUR:WAVE:ABORT')
        print("Keithley 6221 Output DISABLED")


class Keithley2400_DCSource:
    """
    用于控制 Keithley 2400 直流源表 (对应论文中的温度计 Thermometer 探针电流)。
    论文中使用了两台此类仪器 。
    """
    def __init__(self, resource_name):
        self.rm = pyvisa.ResourceManager()
        try:
            self.inst = self.rm.open_resource(resource_name)
            print(f"已连接 Keithley 2400: {self.inst.query('*IDN?')}")
            self.inst.write('*RST')
            time.sleep(1)
        except Exception as e:
            print(f"连接 Keithley 2400 失败: {e}")

    def setup_current_source(self, current_level=10e-6, voltage_compliance=21):
        """
        配置为电流源模式。
        参数:
            current_level (float): 输出电流 (Amp), 例如 10uA
            voltage_compliance (float): 电压保护限值 (Volt)
        """
        try:
            self.inst.write(':SOUR:FUNC CURR')        # 设置为电流源
            self.inst.write(':SOUR:CURR:MODE FIX')    # 固定模式
            self.inst.write(f':SENS:VOLT:PROT {voltage_compliance}') # 设置电压保护
            self.inst.write(f':SOUR:CURR:LEV {current_level}')       # 设置电流值
            print(f"Keithley 2400 configured: DC Current {current_level}A")
        except Exception as e:
            print(f"配置电流源失败: {e}")

    def enable_output(self):
        self.inst.write(':OUTP ON')
        print("Keithley 2400 Output ON")

    def disable_output(self):
        self.inst.write(':OUTP OFF')
        print("Keithley 2400 Output OFF")
class Keithley6221_DCSource:
    """
    用于控制 Keithley 6221 作为直流电流源 (替代 Keithley 2400 的功能)。
    用于给温度计提供恒定的直流探测电流。
    """
    def __init__(self, resource_name):
        self.rm = pyvisa.ResourceManager()
        try:
            self.inst = self.rm.open_resource(resource_name)
            # 查询 IDN 确认连接
            print(f"已连接 Keithley 6221 (DC Mode): {self.inst.query('*IDN?')}")
            self.inst.write('*RST') # 复位仪器，默认回到 DC 模式
            time.sleep(1)
        except Exception as e:
            print(f"连接 Keithley 6221 (DC) 失败: {e}")

    def setup_current_source(self, current_level=10e-6, voltage_compliance=10):
        """
        配置为直流电流源模式。
        参数:
            current_level (float): 输出电流 (Amp), 例如 10uA
            voltage_compliance (float): 电压保护限值 (Volt)
        """
        try:
            # 6221 专用指令
            self.inst.write('SOUR:WAVE:OFF')        # 确保关闭波形模式，进入标准 DC 模式
            self.inst.write('SOUR:CURR:RANG:AUTO ON') # 开启自动量程
            self.inst.write(f'SOUR:CURR:COMP {voltage_compliance}') # 设置电压顺从/保护值 (Compliance)
            self.inst.write(f'SOUR:CURR {current_level}')           # 设置直流电流值
            
            print(f"Keithley 6221 (DC) configured: {current_level}A, Compliance {voltage_compliance}V")
        except Exception as e:
            print(f"配置 6221 直流源失败: {e}")

    def enable_output(self):
        """开启输出"""
        self.inst.write('OUTP ON')
        print("Keithley 6221 (DC) Output ON")

    def disable_output(self):
        """关闭输出"""
        self.inst.write('OUTP OFF')
        print("Keithley 6221 (DC) Output OFF")