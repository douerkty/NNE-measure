# fileName: InstrumentManager.py
from lockin7270_controller import InstrumentLockin7270
from keithley_drivers import Keithley6221_ACSource, Keithley2400_DCSource,Keithley6221_DCSource
from lakeshore_controller import LakeshoreController

class InstrumentManager:
    def __init__(self):
        # 保持原有的变量名，以兼容 MeasurementThread
        self.inst1 = None  # Thermometer 1 Lock-in
        self.inst2 = None  # Thermometer 2 Lock-in
        self.my_instrument_current = None # Heater AC Source (Keithley 6221)
        
        # 新增变量
        self.dc_source1 = None # Thermometer 1 DC Source (Keithley 2400)
        self.dc_source2 = None # Thermometer 2 DC Source (Keithley 2400)

    def connect_instruments(self, inst1_ip, inst2_ip, heater_addr, dc1_addr, dc2_addr):
        """
        连接所有5台仪器。
        注意：参数不仅包含IP，还包含VISA地址 (如 GPIB0::12::INSTR)
        """
        print("Connecting instruments for Fig 1 reproduction...")
        
        # 1. 连接锁相放大器 (7270)
        if not self.inst1:
            self.inst1 = InstrumentLockin7270(inst1_ip)
        if not self.inst2:
            self.inst2 = InstrumentLockin7270(inst2_ip)
            
        # 2. 连接交流加热源 (lakeshore)
        if not self.my_instrument_current:
            print("Connecting Lakeshore Precision Source as heater...")
            self.my_instrument_current = LakeshoreController(ip_address=heater_addr)
        # 修改前 (使用 2400)
        # if not self.dc_source1:
        #     self.dc_source1 = Keithley2400_DCSource(dc1_addr)

        # 修改后 (使用 6221)
        if not self.dc_source1:
            print(f"Connecting DC Source 1 (K6221) to {dc1_addr}...")
            self.dc_source1 = Keithley6221_DCSource(dc1_addr)
        
        if not self.dc_source2:
            print(f"Connecting DC Source 2 (K6221) to {dc2_addr}...")
            self.dc_source2 = Keithley6221_DCSource(dc2_addr)
            
        print("Instruments connected.")
    '''
    def _adapter_output_sine_current(self, amplitude, frequency, offset=0.0, phase=0.0):
        """
        适配器方法：将旧的调用方式转换为 Keithley 6221 的调用方式。
        注意：Keithley 6221 不需要 offset 和 phase 参数，这里忽略它们。
        """
        print(f"Adapter: Setting Keithley 6221 to {frequency}Hz, {amplitude}A")
        # 调用 keithley_drivers.py 中的方法
        self.my_instrument_current.setup_sine_wave(frequency, amplitude)
    '''       
    # 文件名: InstrumentManager.py

    # ... (类定义和 connect_instruments 方法) ...

    def setup_dc_sources(self, current_val=10e-6):
        """配置并开启所有直流源，并设置锁相放大器为 2f 模式。"""
        
        # 1. 配置并开启直流源
        if self.dc_source1 and self.dc_source2:
            self.dc_source1.setup_current_source(current_val)
            self.dc_source1.enable_output()
            self.dc_source2.setup_current_source(current_val)
            self.dc_source2.enable_output()
            print("DC Sources initialized and enabled.")
        
        # 【核心修改：一台锁 2f，一台锁 4f】
        if self.inst1 and self.inst2:
            self.inst1.set_harmonic(2)   # 纵向：2ω (Fig.1e/f + Fig.2a)
            self.inst2.set_harmonic(4)   # 横向：4ω (Fig.2b) ← 必须是 4！
            print("Lock-in 1 → 2f (longitudinal), Lock-in 2 → 4f (transverse NNE)")