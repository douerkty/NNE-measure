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

    def init_plot(self):

        print("Initializing uniform 2x2 grid (Option A)")
        self.fig, axes = plt.subplots(2, 2, figsize=(12, 9))
        ax00 = axes[0, 0]
        ax01 = axes[0, 1]
        ax10 = axes[1, 0]
        ax11 = axes[1, 1]

        # Init default titles/labels for fig1
        ax00.set_title('Fig. 1e: V_long^{2ω} vs I (parabolic)')
        ax00.set_xlabel('Current-AC (A)')
        ax00.set_ylabel('Longitudinal 2ω (V)')

        ax01.set_title('Fig. 1f: V_long^{2ω} vs I² (linear)')
        ax01.set_xlabel('Current-AC² (A²)')
        ax01.set_ylabel('Longitudinal 2ω (V)')

        ax10.set_title('R vs T (R = V_long / I_dc)')
        ax10.set_xlabel('T (K)')
        ax10.set_ylabel('R (Ω)')

        # ax11 reserved and initially hidden
        ax11.set_visible(False)

        # Map modes -> axes and initialize lines
        self.modes = {
            'fig1': {
                'axes': [ax00, ax01, ax10],
                'lines': [None, None, None]
            },
            'fig2': {
                'axes': [ax00, ax01],
                'lines': [None, None]
            }
        }

        # Create empty lines per axis (mode-specific)
        for mk, mode in self.modes.items():
            for i, ax in enumerate(mode['axes']):
                line, = ax.plot([], [], 'o-', lw=2)
                mode['lines'][i] = line

        # Start in fig1 mode
        self.active_mode = None
        self.set_mode('fig1')

    def plot_data(self):
        L = len(self.data['Current-AC'])
        if L == 0:
            return

        I = np.array(self.data['Current-AC'][:L])
        V_long = np.array(self.data['Voltage1'][:L])   # 2ω
        V_trans = np.array(self.data['Voltage3'][:L])  # 4ω
        T = np.array(self.data['Temperature'][:L]) if self.data['Temperature'] else np.array([])
        I_dc_arr = np.array(self.data['Current-DC'][:L]) if self.data['Current-DC'] else np.zeros(L)

        if self.active_mode == 'fig1':
            lines = self.modes['fig1']['lines']
            lines[0].set_data(I, V_long)       # 1e
            lines[1].set_data(I**2, V_long)    # 1f
            if len(T) > 0:
                with np.errstate(divide='ignore', invalid='ignore'):
                    R = np.where(I_dc_arr != 0, V_long / I_dc_arr, np.nan)
                lines[2].set_data(T, R)       # R-T

            # Autoscale axes used by fig1
            for ax in self.modes['fig1']['axes']:
                ax.relim()
                ax.autoscale_view()

        elif self.active_mode == 'fig2':
            lines = self.modes['fig2']['lines']
            lines[0].set_data(I, V_long)       # 2a
            lines[1].set_data(I, V_trans)      # 2b

            # Autoscale axes used by fig2 (top row axes)
            for ax in self.modes['fig2']['axes']:
                ax.relim()
                ax.autoscale_view()

        return

    def _update_data(self, key, value):
        try:
            self.data[key].append(value)
        except KeyError:
            print(f"Error: Key '{key}' not found in data dictionary.")

    def set_mode(self, mode_key: str):

        if mode_key == self.active_mode:
            return

        if mode_key not in self.modes:
            print(f"Unknown mode: {mode_key}")
            return

        # Hide all axes first
        all_axes = set()
        for mode in self.modes.values():
            for ax in mode['axes']:
                all_axes.add(ax)
        for ax in all_axes:
            ax.set_visible(False)

        # Configure and show axes for the selected mode
        if mode_key == 'fig1':
            ax1, ax2, ax_rt = self.modes['fig1']['axes']
            ax1.set_visible(True)
            ax1.set_title('Fig. 1e: V_long^{2ω} vs I (parabolic)')
            ax1.set_xlabel('Current-AC (A)')
            ax1.set_ylabel('Longitudinal 2ω (V)')

            ax2.set_visible(True)
            ax2.set_title('Fig. 1f: V_long^{2ω} vs I² (linear)')
            ax2.set_xlabel('Current-AC² (A²)')
            ax2.set_ylabel('Longitudinal 2ω (V)')

            ax_rt.set_visible(True)
            ax_rt.set_title('R vs T (R = V_long / I_dc)')
            ax_rt.set_xlabel('T (K)')
            ax_rt.set_ylabel('R (Ω)')

        elif mode_key == 'fig2':
            ax2a, ax2b = self.modes['fig2']['axes']
            ax2a.set_visible(True)
            ax2a.set_title('Fig. 2a: V_long^{2ω} vs I (quadratic)')
            ax2a.set_xlabel('I (A)')
            ax2a.set_ylabel(r'$V_x^{2\omega}$ (V)')

            ax2b.set_visible(True)
            ax2b.set_title('Fig. 2b: V_trans^{4ω} vs I (quartic)')
            ax2b.set_xlabel('I (A)')
            ax2b.set_ylabel(r'$V_y^{4\omega}$ (V)')

        # Show lines for active mode and hide others
        for mk, mode in self.modes.items():
            visible = (mk == mode_key)
            for ln in mode['lines']:
                if ln is not None:
                    ln.set_visible(visible)

        self.active_mode = mode_key
        # redraw canvas
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

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
