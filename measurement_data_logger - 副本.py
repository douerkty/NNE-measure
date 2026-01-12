import matplotlib.pyplot as plt
from MultiPyVu import MultiVuClient as mvc
import pandas as pd
import time

class DataLogger:
    DELAY = 0.08
    DEFAULT_FILENAME_PREFIX = "measurement_data"

    def __init__(self):
        self.data = {
            'Temperature': [], 'Field': [],
            'Current-AC': [], 'Current-DC': [],
            'Voltage1': [], 'Phase1': [],
            'Voltage2': [], 'Phase2': [],
            'Voltage3': [], 'Phase3': [],
            'Voltage4': [], 'Phase4': [],
        }
        self.lines = []
        self.fig=None
        self.axes=None

    def init_plot(self):
        print("Initializing the plot...")  # 添加这一行
        self.fig, self.axes = plt.subplots(2,2, figsize=(6, 8))
        for idx,ax in self.axes.ravel():
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 10)
            ax.set_xlabel('Current-AC')
            line, = ax.plot([], [], 'b-')  # 初始化线条但不提供数据
            self.lines.append(line)
            print(ax)

    def _update_data(self, key, value):
        if key in self.data:
            self.data[key].append(value)
        else:
            print(f"Error: Key '{key}' not found in data dictionary.")

    def save_data_to_txt(self, filename_prefix=None):
        filename_prefix = filename_prefix or self.DEFAULT_FILENAME_PREFIX
        last_temp = self.data['Temperature'][-1] if self.data['Temperature'] else 'Unknown'
        temperature_suffix = f"{round(last_temp,2)}K"
        filename = f"{filename_prefix}_{temperature_suffix}.txt"
        df = pd.DataFrame(self.data)
        df.to_csv(filename, sep='\t', index=False)
        print(f"Data saved to {filename}.")

    def plot_data(self):
        keys = ['Voltage1', 'Voltage2', 'Voltage3', 'Voltage4']
        titles = [f'{key} vs Current-AC' for key in keys]
        len_current_ac = len(self.data['Current-AC'])
        for idx, (key, ax, title) in enumerate(zip(keys, self.axes.ravel(), titles)):
            # 使用set_data方法更新线条数据
            self.lines[idx].set_data(self.data['Current-AC'][:len_current_ac], self.data[key][:len_current_ac])
            ax.clear()
            ax.set_title(title)
            ax.set_xlabel(key)
            ax.relim()
            ax.autoscale_view()
            print(ax)
            print(key)
            print(title)


        #self.fig.canvas.draw()
        print(self.data['Voltage1'])
        print(self.data['Current-AC'])


    def update_measurements(self, inst1, inst2, current_ac_value, host, port, current_dc=0):
        # 使用 MultiVuClient 获取温度和磁场值
        #with mvc.MultiVuClient(host, port) as client:
        #    T, sT = client.get_temperature()
        T=300
        #    F, sF = client.get_field()
        F=0

        # 更新温度、磁场、交流电流和直流电流值
        self._update_data('Temperature', T)
        self._update_data('Field', F)
        self._update_data('Current-AC', current_ac_value)
        self._update_data('Current-DC', current_dc)

        try:
            # 从 inst1 读取并更新电压和相位值
            self._update_data('Voltage1', float(inst1.query_voltage1()))
            time.sleep(self.DELAY)
            self._update_data('Phase1', float(inst1.query_phase1()))
            time.sleep(self.DELAY)
            self._update_data('Voltage2', float(inst1.query_voltage2()))
            time.sleep(self.DELAY)
            self._update_data('Phase2', float(inst1.query_phase2()))
            time.sleep(self.DELAY)
            # 从 inst2 读取并更新电压和相位值
            self._update_data('Voltage3', float(inst2.query_voltage1()))
            time.sleep(self.DELAY)
            self._update_data('Phase3', float(inst2.query_phase1()))
            time.sleep(self.DELAY)
            self._update_data('Voltage4', float(inst2.query_voltage2()))
            time.sleep(self.DELAY)
            self._update_data('Phase4', float(inst2.query_phase2()))
            time.sleep(self.DELAY)
            self.plot_data()

        except Exception as e:
            print(f"设备查询过程中出错：{e}")