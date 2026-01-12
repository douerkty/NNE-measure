from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QGroupBox, QListWidget, QFileDialog, QCheckBox)
from PyQt5.QtGui import QColor, QPixmap, QPainter
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from measurement_data_logger import DataLogger
from PyQt5.QtCore import pyqtSlot


class MeasurementGUI(QWidget):
    def __init__(self, start_callback, stop_callback, data_logger):
        super().__init__()

        # Default values
        self.DEFAULT_HOST = "10.16.28.160"
        self.DEFAULT_PORT = 5000
        self.DEFAULT_IP_ADDRESS_INST1 = '10.16.2.73'
        self.DEFAULT_IP_ADDRESS_INST2 = '10.16.39.186'
        self.DEFAULT_CURRENT_IP = '10.16.87.186'

        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.data_logger = data_logger
        self.canvas = FigureCanvas(self.data_logger.fig)

        # Initialize the UI
        self.init_ui()
        self.showMaximized()


    def init_ui(self):
        main_layout = QHBoxLayout()

        # Left side layout
        self.left_layout = QVBoxLayout()

        self._init_indicator_light()
        self._init_status_indicators()
        self._init_folder_selection()
        self._init_instrument_settings()
        self._init_measurement_settings()
        self._init_buttons()
        main_layout.addLayout(self.left_layout, 1)

        # Right side layout (Plot)
        self.right_layout = QVBoxLayout()  # <-- 初始化右侧布局
        self._init_plot()
        main_layout.addLayout(self.right_layout, 5)

        self.setLayout(main_layout)
        self.setWindowTitle("Measurement GUI")

    def _init_plot(self):
        """Initialize the plot."""
        self.canvas = FigureCanvas(self.data_logger.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        self.right_layout.addLayout(plot_layout)

    def _init_indicator_light(self):
        self.indicator_light = QLabel(self)
        self.indicator_light.setPixmap(self._generate_indicator_pixmap(QColor("gray")))
        self.left_layout.addWidget(self.indicator_light,1)

    def _init_instrument_settings(self):
        group_box = QGroupBox("Instrument Settings", self)
        layout = QVBoxLayout()

        self.host_input = self._create_input_field("Host:", self.DEFAULT_HOST, layout)
        self.port_input = self._create_input_field("Port:", str(self.DEFAULT_PORT), layout)
        self.ip_lock1_input = self._create_input_field("IP_Lock1:", self.DEFAULT_IP_ADDRESS_INST1, layout)
        self.ip_lock2_input = self._create_input_field("IP_Lock2:", self.DEFAULT_IP_ADDRESS_INST2, layout)
        # --- 新增：3个 Keithley 仪器的地址输入框 ---
        # 默认值建议写成 VISA 地址格式，方便使用
        self.heater_addr_input = self._create_input_field("Heater IP (Lakeshore):", "10.16.87.186", layout)
        self.dc1_addr_input = self._create_input_field("DC Source 1 (K6221):", "GPIB0::24::INSTR", layout)
        self.dc2_addr_input = self._create_input_field("DC Source 2 (K6221):", "GPIB0::25::INSTR", layout)
        # ---------------------------------------

        group_box.setLayout(layout)
        self.left_layout.addWidget(group_box,2)

    def _init_measurement_settings(self):
        group_box = QGroupBox("Measurement Settings", self)
        layout = QVBoxLayout()
        
        wait_layout = QHBoxLayout()
        self.wait_time_input = QLineEdit("70")                  # 默认值 70 秒
        wait_label = QLabel("Wait Time (seconds):")
        wait_label.setBuddy(self.wait_time_input)
        wait_layout.addWidget(wait_label)
        wait_layout.addWidget(self.wait_time_input)
        layout.addLayout(wait_layout)

        freq_layout = QHBoxLayout()
        self.frequency_input = QLineEdit("17.777")   # 默认就是论文用的频率
        freq_label = QLabel("Heater Frequency (Hz):")
        freq_label.setBuddy(self.frequency_input)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.frequency_input)
        layout.addLayout(freq_layout)

        layout1=QHBoxLayout()
        self.interval1_input1 = self._create_input_field("Initial_Amplitude1:", "3e-4", layout1)
        self.interval1_input2 = self._create_input_field("Final_Amplitude1:", "2e-4", layout1)
        self.interval1_input3 = self._create_input_field("Step_Amplitude1:", "-5e-6", layout1)
        layout.addLayout(layout1)

        layout2 = QHBoxLayout()
        self.interval2_input1 = self._create_input_field("Initial_Amplitude2:", "2e-4", layout2)
        self.interval2_input2 = self._create_input_field("Final_Amplitude2:", "2e-5", layout2)
        self.interval2_input3 = self._create_input_field("Step_Amplitude2:", "-2e-6", layout2)
        layout.addLayout(layout2)

        layout3 = QHBoxLayout()
        self.interval3_input1 = self._create_input_field("Initial_Amplitude3:", "2e-5", layout3)
        self.interval3_input2 = self._create_input_field("Final_Amplitude3:", "2e-6", layout3)
        self.interval3_input3 = self._create_input_field("Step_Amplitude3:", "-5e-7", layout3)
        layout.addLayout(layout3)
        layout4 = QHBoxLayout()
        self.interval4_input1 = self._create_input_field("Initial_Amplitude4:", "2e-6", layout4)
        self.interval4_input2 = self._create_input_field("Final_Amplitude4:", "1e-7", layout4)
        self.interval4_input3 = self._create_input_field("Step_Amplitude4:", "-1e-7", layout4)
        layout.addLayout(layout4)

        self.amplitude_list = QListWidget(self)
        layout.addWidget(self.amplitude_list)
        # Temperature Changing
        self.temp_changing_checkbox = QCheckBox("Temperature Changing", self)
        layout.addWidget(self.temp_changing_checkbox)

        self.initial_temp_input = self._create_input_field("Initial_Temp:", "20", layout)
        self.final_temp_input = self._create_input_field("Final_Temp:", "30", layout)
        self.step_temp_input = self._create_input_field("Step_Temp:", "1", layout)
        self.rate_input = self._create_input_field("Rate:", "1", layout)
        group_box.setLayout(layout)
        self.left_layout.addWidget(group_box,10)

    def _init_status_indicators(self):
        """Initialize the status indicators for temperature and amplitude."""
        status_layout = QVBoxLayout()

        # Temperature indicator
        temp_label = QLabel("Current Temperature:", self)
        self.temp_display = QLineEdit(self)
        self.temp_display.setReadOnly(True)
        status_layout.addWidget(temp_label)
        status_layout.addWidget(self.temp_display)

        # Amplitude indicator
        amplitude_label = QLabel("Current Amplitude:", self)
        self.amplitude_display = QLineEdit(self)
        self.amplitude_display.setReadOnly(True)
        status_layout.addWidget(amplitude_label)
        status_layout.addWidget(self.amplitude_display)

        self.left_layout.addLayout(status_layout,1)

    def _create_input_field(self, label_text, default_value, layout):
        label = QLabel(label_text, self)
        layout.addWidget(label)
        input_field = QLineEdit(default_value, self)
        layout.addWidget(input_field)
        return input_field

    def _init_buttons(self):
        self.start_button = QPushButton("Start Measurement", self)
        self.start_button.clicked.connect(self._start_button_clicked)
        self.left_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Measurement", self)
        self.stop_button.clicked.connect(self._stop_button_clicked)
        self.left_layout.addWidget(self.stop_button)


    def _start_button_clicked(self):
        # Extracting values and handling potential errors
        self.turn_on_indicator()
        try:
            host = self.host_input.text()
            port = int(self.port_input.text())
            ip1 = self.ip_lock1_input.text()
            ip2 = self.ip_lock2_input.text()
            # --- 新增：获取新输入框的文本 ---
            heater_addr = self.heater_addr_input.text()
            dc1_addr = self.dc1_addr_input.text()
            dc2_addr = self.dc2_addr_input.text()
            # ----------------------------- 
            initial1_Amplitude = float(self.interval1_input1.text())
            final1_Amplitude= float(self.interval1_input2.text())
            step1_Amplitude = float(self.interval1_input3.text())
            initial2_Amplitude = float(self.interval2_input1.text())
            final2_Amplitude = float(self.interval2_input2.text())
            step2_Amplitude = float(self.interval2_input3.text())
            initial3_Amplitude = float(self.interval3_input1.text())
            final3_Amplitude = float(self.interval3_input2.text())
            step3_Amplitude = float(self.interval3_input3.text())
            initial4_Amplitude = float(self.interval4_input1.text())
            final4_Amplitude = float(self.interval4_input2.text())
            step4_Amplitude = float(self.interval4_input3.text())
        except ValueError:
            print("Error: Invalid input values.")
            return
        temperature_changing = self.temp_changing_checkbox.isChecked()
        print("Temperature changing checkbox status:", temperature_changing)
        if temperature_changing:
            try:
                initial_temp = float(self.initial_temp_input.text())
                final_temp = float(self.final_temp_input.text())
                step_temp = float(self.step_temp_input.text())
                rate = float(self.rate_input.text())
                print(
                    f"Temperature Changing Parameters: Initial: {initial_temp}, Final: {final_temp}, Step: {step_temp}, Rate: {rate}")
            except ValueError:
                print("Error: Invalid temperature settings.")
                return
        else:
            initial_temp, final_temp, step_temp, rate = None, None, None, None
        print("Before updating global_color_idx.")
        DataLogger.global_color_idx += 1
        print("After updating global_color_idx.")
        print("Current color index:", DataLogger.global_color_idx)
        wait_time = float(self.wait_time_input.text())
        frequency = float(self.frequency_input.text())
        
        self.start_callback(host, port, ip1, ip2, heater_addr,dc1_addr,dc2_addr,
                            initial1_Amplitude,final1_Amplitude,step1_Amplitude,initial2_Amplitude,final2_Amplitude,step2_Amplitude,
                            initial3_Amplitude,final3_Amplitude,step3_Amplitude,initial4_Amplitude,final4_Amplitude,step4_Amplitude, 
                            wait_time, temperature_changing,initial_temp,final_temp,step_temp,rate, frequency)

    def _stop_button_clicked(self):
        if hasattr(self, "measurement_thread"):  # Check if the attribute exists
            self.measurement_thread.stop_requested = True
        self.stop_callback()

    def _generate_indicator_pixmap(self, color):
        pixmap = QPixmap(20, 20)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("transparent"))
        painter.setBrush(color)
        painter.drawEllipse(0, 0, 20, 20)
        painter.end()
        return pixmap

    def turn_on_indicator(self):
        self.indicator_light.setPixmap(self._generate_indicator_pixmap(QColor("green")))

    def turn_off_indicator(self):
        self.indicator_light.setPixmap(self._generate_indicator_pixmap(QColor("red")))

    def update_amplitude_list(self, amplitude_values):
        self.amplitude_list.clear()  # 清除当前内容
        for value in amplitude_values:
            self.amplitude_list.addItem(str(value))

    def _init_folder_selection(self):
        group_box = QGroupBox("File Location", self)
        layout = QVBoxLayout()

        # Folder selection components
        self.folder_input = QLineEdit(self)
        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self._browse_folder)
        layout.addWidget(self.folder_input)
        layout.addWidget(self.browse_button)

        group_box.setLayout(layout)
        self.left_layout.addWidget(group_box)

    def _browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:  # make sure user didn't cancel the dialog
            self.folder_input.setText(folder_path)
        else:  # if user cancelled the dialog, set to default directory
            import os
            self.folder_input.setText(os.getcwd())

    def update_temperature_display(self, temperature):
        """Update the temperature display."""
        self.temp_display.setText(str(temperature))

    def update_amplitude_display(self, amplitude):
        """Update the amplitude display."""
        self.amplitude_display.setText(str(amplitude))

    @pyqtSlot(float, float)
    def update_temperature_amplitude(self, temperature, amplitude):
        self.update_temperature_display(temperature)
        self.update_amplitude_display(amplitude)


    def refresh_plot(self):
        """Refreshes the canvas."""
        print("Refreshing the plot...")
        self.canvas.draw()


