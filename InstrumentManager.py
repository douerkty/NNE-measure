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

    def connect_instruments(self, inst1_ip, inst2_ip, heater_addr, dc1_addr=None, dc2_addr=None, mode='fig1', harm1=2, harm2=4):
        """
        连接仪器。根据 `mode` 决定是否连接直流源 (用于 Fig.1 系列)
        注意：参数既可以是 IP，也可以是 VISA 地址 (如 GPIB0::12::INSTR)
        """
        print(f"Connecting instruments for mode '{mode}'...")
        
        # 1. 连接锁相放大器 (7270)
        if not self.inst1 and inst1_ip:
            self.inst1 = InstrumentLockin7270(inst1_ip)
        if not self.inst2 and inst2_ip:
            self.inst2 = InstrumentLockin7270(inst2_ip)
            
        # 2. 连接加热器 (Lakeshore)
        if not self.my_instrument_current and heater_addr:
            print("Connecting Lakeshore controller as heater...")
            self.my_instrument_current = LakeshoreController(ip_address=heater_addr)

        # 3. 只有在 fig1 (Fig.1e/1f) 模式下才连接并设置直流源
        if mode == 'fig1':
            if not self.dc_source1 and dc1_addr:
                print(f"Connecting DC Source 1 (K6221) to {dc1_addr}...")
                self.dc_source1 = Keithley6221_DCSource(dc1_addr)
            if not self.dc_source2 and dc2_addr:
                print(f"Connecting DC Source 2 (K6221) to {dc2_addr}...")
                self.dc_source2 = Keithley6221_DCSource(dc2_addr)
            print("Fig.1 mode instruments connected (including DC sources).")
        else:
            print("Fig.2 mode: skipping DC source connection (not required).")

        # 设置锁相谐波 (如果锁相存在)
        if self.inst1 and self.inst2:
            print(f"Setting Lock-in Harmonics: Inst1 -> {harm1}f, Inst2 -> {harm2}f")
            self.inst1.set_harmonic(harm1)
            self.inst2.set_harmonic(harm2)

        print("Instruments connected.")

    # ... (类定义和 connect_instruments 方法) ...

    def setup_dc_sources(self, current_val=10e-6,harm1=2, harm2=4):
        """配置并开启所有直流源，并设置锁相放大器默认为 2f和4f 模式。"""
        
        # 1. 配置并开启直流源
        if self.dc_source1 and self.dc_source2:
            self.dc_source1.setup_current_source(current_val)
            self.dc_source1.enable_output()
            self.dc_source2.setup_current_source(current_val)
            self.dc_source2.enable_output()
            print("DC Sources initialized and enabled.")
        
        if self.inst1 and self.inst2:
            print(f"Setting Lock-in Harmonics: Inst1 -> {harm1}f, Inst2 -> {harm2}f")
            self.inst1.set_harmonic(harm1)
            self.inst2.set_harmonic(harm2)