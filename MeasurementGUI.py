
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QGroupBox,
    QFileDialog, QComboBox, QCheckBox, QListWidget, QMessageBox, QTabWidget, QFormLayout
)
from PyQt5.QtGui import QColor, QPixmap, QPainter
from PyQt5.QtCore import pyqtSlot
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np


class MeasurementGUIRefactored(QWidget):
    """
    Refactored GUI focused on:
      - Mode: Fig.1e/1f or Fig.2a/2b (measured separately)
      - Two lock-ins: selectable harmonic for each
      - Two K6221: DC current setpoint for each
      - Lakeshore: AC amplitude sweep + frequency
      - PPMS: temperature control only (host/port + target T + rate + stable options)

    This GUI calls:
      - start_callback(config: dict)
      - stop_callback()
    """

    def __init__(self, start_callback, stop_callback, data_logger):
        super().__init__()

        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.data_logger = data_logger
    
        # Defaults (kept from your current GUI)
        self.DEFAULT_PPMS_HOST = "10.16.28.160"
        self.DEFAULT_PPMS_PORT = "5000"
        self.DEFAULT_IP_LOCK1 = "10.16.2.73"
        self.DEFAULT_IP_LOCK2 = "10.16.39.186"
        self.DEFAULT_LAKESHORE_IP = "10.16.87.186"
        self.DEFAULT_DC1_ADDR = "GPIB0::24::INSTR"
        self.DEFAULT_DC2_ADDR = "GPIB0::25::INSTR"

        self._build_ui()
        self.showMaximized()
        # 修改模式下拉菜单
        self.mode_combo.clear()
        self.mode_combo.addItems(["Fig.1e/1f + R-T", "Fig.2a/2b"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
    # ---------------- UI ----------------
    def _build_ui(self):
        main_layout = QHBoxLayout(self)

        # Left: controls
        left = QVBoxLayout()
        self._init_indicator(left)
        self._init_statusbox(left)
        self._init_tabs(left)
        self._init_run_controls(left)
        main_layout.addLayout(left, 1)

        # Right: plot
        right = QVBoxLayout()
        self.canvas = FigureCanvas(self.data_logger.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        right.addWidget(self.toolbar)
        right.addWidget(self.canvas)
        main_layout.addLayout(right, 4)

        self.setWindowTitle("NNE Measurement GUI (Refactored)")

    def _init_indicator(self, parent_layout):
        row = QHBoxLayout()
        self.indicator_light = QLabel(self)
        self.indicator_light.setPixmap(self._indicator_pixmap(QColor("gray")))
        row.addWidget(QLabel("Status:", self))
        row.addWidget(self.indicator_light)
        row.addStretch(1)
        parent_layout.addLayout(row)

    def _init_statusbox(self, parent_layout):
        box = QGroupBox("Live Status", self)
        layout = QVBoxLayout()

        self.status_line = QLabel("Idle", self)
        self.temp_line = QLabel("T: -- K", self)
        self.ih_line = QLabel("Ih: -- A", self)

        layout.addWidget(self.status_line)
        layout.addWidget(self.temp_line)
        layout.addWidget(self.ih_line)

        box.setLayout(layout)
        parent_layout.addWidget(box)

    def _init_tabs(self, parent_layout):
        tabs = QTabWidget(self)

        tabs.addTab(self._tab_mode(), "Mode")
        tabs.addTab(self._tab_ppms(), "PPMS")
        tabs.addTab(self._tab_instruments(), "Instruments")
        tabs.addTab(self._tab_heater_sweep(), "Heater Sweep")
        tabs.addTab(self._tab_data(), "Data")

        parent_layout.addWidget(tabs, 10)

        # set mode defaults once lockin controls exist
        self._apply_mode_defaults()

    def _tab_mode(self):
        w = QWidget(self)
        form = QFormLayout(w)

        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems([
            "Fig.1e/1f (Thermometers ΔR/R, two lock-ins @ 2ω)",
            "Fig.2a/2b (Thermoelectric: Vx@2ω, Vy@4ω)"
        ])
        form.addRow("Measurement mode:", self.mode_combo)

        # Convenience: auto-fill harmonics when mode changes (still editable)
        self.mode_combo.currentIndexChanged.connect(self._apply_mode_defaults)
        return w

    def _tab_ppms(self):
        w = QWidget(self)
        form = QFormLayout(w)

        self.ppms_host = QLineEdit(self.DEFAULT_PPMS_HOST, self)
        self.ppms_port = QLineEdit(self.DEFAULT_PPMS_PORT, self)
        form.addRow("PPMS Host:", self.ppms_host)
        form.addRow("PPMS Port:", self.ppms_port)

        self.ppms_enable = QCheckBox("Control temperature before measurement", self)
        self.ppms_enable.setChecked(True)
        form.addRow(self.ppms_enable)

        self.ppms_target_T = QLineEdit("20", self)
        self.ppms_rate = QLineEdit("1", self)
        form.addRow("Target T (K):", self.ppms_target_T)
        form.addRow("Rate (K/min):", self.ppms_rate)

        # "Advanced but useful"
        self.ppms_tol = QLineEdit("0.02", self)      # K
        self.ppms_stable_sec = QLineEdit("60", self) # seconds
        self.ppms_timeout_min = QLineEdit("30", self)
        form.addRow("Stability tol (K):", self.ppms_tol)
        form.addRow("Stable for (s):", self.ppms_stable_sec)
        form.addRow("Timeout (min):", self.ppms_timeout_min)

        return w

    def _tab_instruments(self):
        w = QWidget(self)
        layout = QVBoxLayout(w)

        # Lock-ins
        lock_box = QGroupBox("Lock-ins (7270)", self)
        lock_form = QFormLayout(lock_box)

        self.lock1_ip = QLineEdit(self.DEFAULT_IP_LOCK1, self)
        self.lock2_ip = QLineEdit(self.DEFAULT_IP_LOCK2, self)

        self.lock1_harm = QComboBox(self)
        self.lock2_harm = QComboBox(self)
        for cb in (self.lock1_harm, self.lock2_harm):
            cb.addItems([str(i) for i in range(1, 9)])

        lock_form.addRow("Lock-in 1 IP:", self.lock1_ip)
        lock_form.addRow("Lock-in 1 harmonic:", self.lock1_harm)
        lock_form.addRow("Lock-in 2 IP:", self.lock2_ip)
        lock_form.addRow("Lock-in 2 harmonic:", self.lock2_harm)

        self.lock_phase_preset = QCheckBox("Apply phase preset (odd=0°, even=90°)", self)
        self.lock_phase_preset.setChecked(True)
        lock_form.addRow(self.lock_phase_preset)

        self.lock_auto_sen = QCheckBox("Auto sensitivity", self)
        self.lock_auto_sen.setChecked(True)
        lock_form.addRow(self.lock_auto_sen)

        # DC sources (K6221)
        # 存为 self.dc_box 以便在模式切换时显示/隐藏
        self.dc_box = QGroupBox("Keithley 6221 (DC probing)", self)
        dc_form = QFormLayout(self.dc_box)

        self.dc1_addr = QLineEdit(self.DEFAULT_DC1_ADDR, self)
        self.dc2_addr = QLineEdit(self.DEFAULT_DC2_ADDR, self)
        self.idc1 = QLineEdit("1e-6", self)
        self.idc2 = QLineEdit("1e-6", self)

        dc_form.addRow("6221 #1 VISA:", self.dc1_addr)
        dc_form.addRow("Idc #1 (A):", self.idc1)
        dc_form.addRow("6221 #2 VISA:", self.dc2_addr)
        dc_form.addRow("Idc #2 (A):", self.idc2)

        # Lakeshore (heater)
        heater_box = QGroupBox("Lakeshore (Heater AC current)", self)
        heater_form = QFormLayout(heater_box)

        self.lakeshore_ip = QLineEdit(self.DEFAULT_LAKESHORE_IP, self)
        self.heater_freq = QLineEdit("17.777", self)
        heater_form.addRow("Lakeshore IP:", self.lakeshore_ip)
        heater_form.addRow("Frequency (Hz):", self.heater_freq)

        layout.addWidget(lock_box)
        layout.addWidget(self.dc_box)
        layout.addWidget(heater_box)
        layout.addStretch(1)

        # Ensure DC controls visibility reflects initial mode selection
        try:
            self._apply_mode_defaults()
        except Exception:
            pass

        return w

    def _tab_heater_sweep(self):
        w = QWidget(self)
        layout = QVBoxLayout(w)

        sweep_box = QGroupBox("Heater AC amplitude sweep", self)
        form = QFormLayout(sweep_box)

        self.sweep_type = QComboBox(self)
        self.sweep_type.addItems(["Linear", "Log (per decade)"])
        form.addRow("Sweep type:", self.sweep_type)

        # Linear
        self.lin_start = QLineEdit("3e-4", self)
        self.lin_stop = QLineEdit("1e-7", self)
        self.lin_step = QLineEdit("-5e-6", self)
        form.addRow("Linear start (A):", self.lin_start)
        form.addRow("Linear stop (A):", self.lin_stop)
        form.addRow("Linear step (A):", self.lin_step)

        # Log
        self.log_imin = QLineEdit("1e-7", self)
        self.log_imax = QLineEdit("3e-4", self)
        self.log_ppd = QLineEdit("10", self)  # points per decade
        form.addRow("Log Imin (A):", self.log_imin)
        form.addRow("Log Imax (A):", self.log_imax)
        form.addRow("Points/decade:", self.log_ppd)

        self.preview_btn = QPushButton("Preview points", self)
        self.preview_btn.clicked.connect(self._preview_points)
        form.addRow(self.preview_btn)

        self.points_list = QListWidget(self)
        layout.addWidget(sweep_box)
        layout.addWidget(self.points_list, 5)

        return w

    def _tab_data(self):
        w = QWidget(self)
        form = QFormLayout(w)

        self.wait_time = QLineEdit("70", self)
        form.addRow("Wait time per point (s):", self.wait_time)

        self.r0_enable = QCheckBox("Use R0 inputs to compute ΔR/R (Fig.1e)", self)
        self.r0_enable.setChecked(False)
        form.addRow(self.r0_enable)

        self.r0_1 = QLineEdit("", self)
        self.r0_2 = QLineEdit("", self)
        form.addRow("R0 Thermometer1 (Ω):", self.r0_1)
        form.addRow("R0 Thermometer2 (Ω):", self.r0_2)

        # Folder
        row = QHBoxLayout()
        self.folder_input = QLineEdit(self)
        self.browse_btn = QPushButton("Browse", self)
        self.browse_btn.clicked.connect(self._browse_folder)
        row.addWidget(self.folder_input)
        row.addWidget(self.browse_btn)

        wrap = QWidget(self)
        wrap.setLayout(row)
        form.addRow("Save folder:", wrap)

        return w

    def _init_run_controls(self, parent_layout):
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start", self)
        self.stop_btn = QPushButton("Stop", self)
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        parent_layout.addLayout(btn_row)

    def _apply_mode_defaults(self):
        # Called after mode selection changes; safe even before lockin widgets exist.
        if not hasattr(self, "lock1_harm"):
            return
        text = self.mode_combo.currentText()
        if text.startswith("Fig.1e/1f"):
            self.lock1_harm.setCurrentText("2")
            self.lock2_harm.setCurrentText("2")
            # Show DC sources controls in Fig.1 modes
            if hasattr(self, 'dc_box'):
                self.dc_box.setVisible(True)
        else:
            self.lock1_harm.setCurrentText("2")
            self.lock2_harm.setCurrentText("4")
            # Hide DC sources controls in Fig.2 modes, and clear DC currents
            if hasattr(self, 'dc_box'):
                self.dc_box.setVisible(False)
                try:
                    self.idc1.setText("0.0")
                    self.idc2.setText("0.0")
                except Exception:
                    pass

    def _on_mode_changed(self, index):
        """Signal handler for mode combo changes (Qt passes index).

        Keeps backward-compatible behavior by applying mode defaults and
        performing any future mode-specific updates here.
        """
        # Ensure the UI reflects the selected mode
        self._apply_mode_defaults()
        # Map to DataLogger mode keys and tell the data logger to switch
        mode_key = "fig1" if self.mode_combo.currentText().startswith("Fig.1e") or "R-T" in self.mode_combo.currentText() else "fig2"
        try:
            # data_logger may not exist in unit tests, so guard
            if hasattr(self, 'data_logger') and hasattr(self.data_logger, 'set_mode'):
                self.data_logger.set_mode(mode_key)
        except Exception as e:
            print(f"Error switching mode on data logger: {e}")

    def _preview_points(self):
        try:
            points = self._build_heater_points()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid sweep", str(e))
            return

        self.points_list.clear()
        max_show = 2000
        for i, v in enumerate(points[:max_show]):
            self.points_list.addItem(f"{i:04d}: {v:.6g}")
        if len(points) > max_show:
            self.points_list.addItem(f"... ({len(points)} points total)")

    def _browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.folder_input.setText(folder_path)

    def _on_start(self):
        try:
            config = self._collect_config()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return

        self.turn_on_indicator()
        self.status_line.setText("Running...")
        self.start_callback(config)

    def _on_stop(self):
        self.stop_callback()
        self.turn_off_indicator()
        self.status_line.setText("Stopped")

    # ---------------- helpers ----------------
    def _collect_config(self) -> dict:
        # PPMS
        ppms = {
            "host": self.ppms_host.text().strip(),
            "port": int(self.ppms_port.text().strip()),
            "enable": self.ppms_enable.isChecked(),
            "target_T": float(self.ppms_target_T.text().strip()),
            "rate": float(self.ppms_rate.text().strip()),
            "tol": float(self.ppms_tol.text().strip()),
            "stable_sec": float(self.ppms_stable_sec.text().strip()),
            "timeout_min": float(self.ppms_timeout_min.text().strip()),
        }

        lockins = {
            "lock1_ip": self.lock1_ip.text().strip(),
            "lock2_ip": self.lock2_ip.text().strip(),
            "lock1_harm": int(self.lock1_harm.currentText()),
            "lock2_harm": int(self.lock2_harm.currentText()),
            "apply_phase_preset": self.lock_phase_preset.isChecked(),
            "auto_sensitivity": self.lock_auto_sen.isChecked(),
        }

        sources = {
            "lakeshore_ip": self.lakeshore_ip.text().strip(),
            "heater_freq": float(self.heater_freq.text().strip()),
            "dc1_addr": self.dc1_addr.text().strip(),
            "dc2_addr": self.dc2_addr.text().strip(),
            "idc1": float(self.idc1.text().strip()),
            "idc2": float(self.idc2.text().strip()),
        }

        sweep = {
            "type": self.sweep_type.currentText(),
            "points": self._build_heater_points(),
        }

        data = {
            "wait_time": float(self.wait_time.text().strip()),
            "save_folder": self.folder_input.text().strip(),
            "use_r0": self.r0_enable.isChecked(),
            "r0_1": float(self.r0_1.text().strip()) if self.r0_enable.isChecked() and self.r0_1.text().strip() else None,
            "r0_2": float(self.r0_2.text().strip()) if self.r0_enable.isChecked() and self.r0_2.text().strip() else None,
        }

        mode = {
            "mode_text": self.mode_combo.currentText(),
            "mode_key": "fig1" if self.mode_combo.currentText().startswith("Fig.1e/1f") else "fig2",
        }

        return {"mode": mode, "ppms": ppms, "lockins": lockins, "sources": sources, "sweep": sweep, "data": data}

    def _build_heater_points(self):
        t = self.sweep_type.currentText()

        if t.startswith("Linear"):
            start = float(self.lin_start.text().strip())
            stop = float(self.lin_stop.text().strip())
            step = float(self.lin_step.text().strip())
            if step == 0:
                raise ValueError("Linear step cannot be 0.")
            if step > 0 and start > stop:
                raise ValueError("Linear step is positive but start > stop.")
            if step < 0 and start < stop:
                raise ValueError("Linear step is negative but start < stop.")

            points = []
            v = start
            max_n = 20000
            n = 0
            if step > 0:
                while v <= stop + 1e-30 and n < max_n:
                    points.append(float(v))
                    v += step
                    n += 1
            else:
                while v >= stop - 1e-30 and n < max_n:
                    points.append(float(v))
                    v += step
                    n += 1
            if n >= max_n:
                raise ValueError("Too many sweep points (linear).")
            return points

        # Log sweep (descending from Imax to Imin, typical for your usage)
        imin = float(self.log_imin.text().strip())
        imax = float(self.log_imax.text().strip())
        ppd = int(float(self.log_ppd.text().strip()))
        if imin <= 0 or imax <= 0:
            raise ValueError("Log sweep requires positive Imin/Imax.")
        if imin >= imax:
            raise ValueError("Log sweep requires Imin < Imax.")
        if ppd <= 0 or ppd > 200:
            raise ValueError("Points/decade should be between 1 and 200.")

        decades = np.log10(imax) - np.log10(imin)
        npts = int(np.ceil(decades * ppd)) + 1
        points = np.logspace(np.log10(imax), np.log10(imin), npts)
        return [float(x) for x in points]

    def _indicator_pixmap(self, color: QColor):
        pixmap = QPixmap(18, 18)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("transparent"))
        painter.setBrush(color)
        painter.drawEllipse(0, 0, 18, 18)
        painter.end()
        return pixmap

    def turn_on_indicator(self):
        self.indicator_light.setPixmap(self._indicator_pixmap(QColor("green")))

    def turn_off_indicator(self):
        self.indicator_light.setPixmap(self._indicator_pixmap(QColor("red")))

    # ---------------- external updates ----------------
    def refresh_plot(self):
        # Called in the GUI thread via signal from the worker thread.
        # Let the data logger recompute line data and autoscale, then draw once.
        try:
            if hasattr(self, 'data_logger') and hasattr(self.data_logger, 'plot_data'):
                self.data_logger.plot_data()
        except Exception as e:
            print(f"Error in refresh_plot: {e}")
        # Draw the canvas in the GUI thread only
        self.canvas.draw()

    def update_temperature_display(self, temperature):
        self.temp_line.setText(f"T: {temperature} K")

    def update_amplitude_display(self, amplitude):
        self.ih_line.setText(f"Ih: {amplitude} A")

    @pyqtSlot(float, float)
    def update_temperature_amplitude(self, temperature, amplitude):
        self.update_temperature_display(temperature)
        self.update_amplitude_display(amplitude)


class MeasurementGUI(MeasurementGUIRefactored):
    """Compatibility wrapper that provides the older API expected by MeasurementApp.

    - Adds `update_amplitude_list(amplitudes)` used by the legacy app code.
    - Keeps the new refactored behavior otherwise.
    """
    def update_amplitude_list(self, amplitudes):
        # Populate the points list with a compact preview of amplitudes
        self.points_list.clear()
        max_show = 2000
        for i, v in enumerate(amplitudes[:max_show]):
            self.points_list.addItem(f"{i:04d}: {v:.6g}")
        if len(amplitudes) > max_show:
            self.points_list.addItem(f"... ({len(amplitudes)} points total)")
