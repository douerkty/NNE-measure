import matplotlib.pyplot as plt
import pandas as pd
import time
import os
from PyQt5.QtCore import QObject, pyqtSignal
from MultiPyVu import MultiVuClient as mvc
import datetime
import numpy as np


class DataLogger(QObject):
    DELAY = 0.1
    DEFAULT_FILENAME_PREFIX = "measurement_data"
    # 定义颜色列表
    COLORS = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
    global_color_idx = 0  # 全局颜色索引，用于跟踪当前的颜色

    index = 0  # Index to keep track of the current color and marker

    updateTemperatureAmplitude = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.data = {
            'Temperature': [], 'Field': [],
            'Current-AC': [], 
            'Current-AC-Squared': [], # 新增：存储电流平方
            'Current-DC': [],
            'Voltage1': [], 'Phase1': [],
            'Voltage2': [], 'Phase2': [],
            'Voltage3': [], 'Phase3': [],
            'Voltage4': [], 'Phase4': [],
        }
        self.lines = []
        self.fig = None
        self.axes = None
        self.save_directory = os.getcwd()
    '''
    def init_plot(self):
        print("Initializing the plot for Fig 1e and 1f...")
        self.fig, self.axes = plt.subplots(2, 2, figsize=(10, 8)) # 调整布局
        
        # Plot 1: 对应 Fig 1e (T vs I)
        ax1 = self.axes[0, 0]
        ax1.set_xlabel('Current-AC (A)')
        ax1.set_ylabel('Thermometer Signal (V) ~ Delta T')
        ax1.set_title('Fig 1e: Signal vs I (Parabolic)')
        
        # Plot 2: 对应 Fig 1f (T vs I^2)
        ax2 = self.axes[0, 1]
        ax2.set_xlabel('Current-AC Squared (A^2)')
        ax2.set_ylabel('Thermometer Signal (V) ~ Delta T')
        ax2.set_title('Fig 1f: Signal vs I^2 (Linear)')

        # 初始化线条
        self.lines = []
        # Line for Thermometer 1 (Fig 1e)
        line1, = ax1.plot([], [], 'r-o', label='Thermometer 1')
        self.lines.append(line1)
        # Line for Thermometer 1 (Fig 1f)
        line2, = ax2.plot([], [], 'r-o', label='Thermometer 1 (vs I^2)')
        self.lines.append(line2)
        
        # ... (可以为第二个温度计添加更多线条) ...
        ax1.legend()
        ax2.legend()
    '''
    def init_plot(self):
        print("Initializing 4-panel plot: Fig.1e/f (top) + Fig.2a/b (bottom)")
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 9))
        
        # Top row: Fig. 1e/f (纵向 2ω)
        self.axes[0,0].set_title('Fig. 1e: V_long^{2ω} vs I (parabolic)')
        self.axes[0,0].set_xlabel('Current-AC (A)')
        self.axes[0,0].set_ylabel('Longitudinal 2ω (V)')

        self.axes[0,1].set_title('Fig. 1f: V_long^{2ω} vs I² (linear)')
        self.axes[0,1].set_xlabel('Current-AC² (A²)')
        self.axes[0,1].set_ylabel('Longitudinal 2ω (V)')

        # Bottom row: Fig. 2a/b
        self.axes[1,0].set_title('Fig. 2a: V_long^{2ω} vs I (quadratic)')
        self.axes[1,0].set_xlabel('I (A)')
        self.axes[1,0].set_ylabel(r'$V_x^{2\omega}$ (V)')

        self.axes[1,1].set_title('Fig. 2b: V_trans^{4ω} vs I (quartic)')
        self.axes[1,1].set_xlabel(r'I (A)')
        self.axes[1,1].set_ylabel(r'$V_y^{4\omega}$ (V)')

        self.lines = []
        for ax in self.axes.ravel():
            line, = ax.plot([], [], 'o-', lw=2)
            self.lines.append(line)

    def plot_data(self):
        L = len(self.data['Current-AC'])
        if L == 0: return
        I = np.array(self.data['Current-AC'][:L])

        # 假设 Voltage1 = 纵向 2ω, Voltage3 = 横向 4ω（如果不是，换成 Voltage2/Voltage4）
        V_long = np.array(self.data['Voltage1'][:L])   # 2ω
        V_trans = np.array(self.data['Voltage3'][:L])  # 4ω

        # Top-left: Fig.1e
        self.lines[0].set_data(I, V_long)
        # Top-right: Fig.1f
        self.lines[1].set_data(I**2, V_long)
        # Bottom-left: Fig.2a
        self.lines[2].set_data(I, V_long)
        # Bottom-right: Fig.2b
        self.lines[3].set_data(I, V_trans)

        for ax in self.axes.ravel():
            ax.relim()
            ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()    
    def _update_data(self, key, value):
        try:
            self.data[key].append(value)
        except KeyError:
            print(f"Error: Key '{key}' not found in data dictionary.")

    def save_data_to_txt(self, filename_prefix=None):
        try:
            filename_prefix = filename_prefix or self.DEFAULT_FILENAME_PREFIX
            last_temp = self.data['Temperature'][-1] if self.data['Temperature'] else 'Unknown'
            temperature_suffix = f"{round(last_temp, 2)}K"
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
            filename = f"{filename_prefix}_{temperature_suffix}_{current_date}.txt"

            # 将文件名与保存目录结合
            full_path = os.path.join(self.save_directory, filename)

            df = pd.DataFrame(self.data)
            df.to_csv(full_path, sep='\t', index=False)
            print(f"Data saved to {full_path}.")
        except Exception as e:
            print(f"Error saving data: {e}")

    def set_save_directory(self, directory):
        self.save_directory = directory

    def update_measurements(self, inst1, inst2, amplitude, host, port,current_dc_value):
        print("begin")
        with mvc.MultiVuClient(host, port) as client:
            time.sleep(5)
            T, sT = client.get_temperature()
            F, sF = client.get_field()
        #T, F = 300, 0  # Placeholder values for temperature and field

        temperature=T
        amplitude=amplitude
        # --- 新增计算 ---
        current_ac_sq = amplitude ** 2
        current_dc= current_dc_value
        # 发射信号
        self.updateTemperatureAmplitude.emit(temperature, amplitude)
        self._update_data('Temperature', T)
        self._update_data('Field', F)
        self._update_data('Current-AC', amplitude)
        self._update_data('Current-DC', current_dc)
        self._update_data('Current-AC-Squared', current_ac_sq) # 存储平方值
        try:
            # Fetch and update values from inst1
            self._fetch_and_update(inst1, ['Voltage1', 'Phase1', 'Voltage2', 'Phase2'])
            # Fetch and update values from inst2
            self._fetch_and_update(inst2, ['Voltage1', 'Phase1', 'Voltage2', 'Phase2'], ['Voltage3', 'Phase3', 'Voltage4', 'Phase4'])
            self.plot_data()
        except Exception as e:
            print(f"Error during device query: {e}")

    def _fetch_and_update(self, inst, query_keys, data_keys=None):
        if data_keys is None:
            data_keys = query_keys

        for query_key, data_key in zip(query_keys, data_keys):
            value = float(getattr(inst, f"query_{query_key.lower()}")())
            time.sleep(self.DELAY)
            self._update_data(data_key, value)
