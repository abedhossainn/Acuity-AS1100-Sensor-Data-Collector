"""Main GUI window for AS1100 sensor data collection application."""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QFileDialog, QStatusBar, QGroupBox, QFormLayout,
    QTextEdit, QMessageBox, QProgressBar, QAbstractItemView, QHeaderView,
)
from PySide6.QtCore import Qt, Slot, QSettings

from app.domain.models import (
    MeasurementMode, IntervalMode, Unit, CollectionConfig
)
from app.sensor.serial_client import AcuitySensorClient
from app.workers.acquisition_worker import AcquisitionWorker
from app.io.csv_exporter import CSVExporter


class MainWindow(QMainWindow):
    """Main application window."""
    
    FREQUENCY_PRESETS = {
        "100": 100.0,
        "50": 50.0,
        "20": 20.0,
        "10": 10.0,
        "5": 5.0,
        "2": 2.0,
        "1": 1.0,
    }
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.setWindowTitle("AS1100 Sensor Data Collector")
        self.setGeometry(100, 100, 1200, 800)
        
        # State
        self.worker: Optional[AcquisitionWorker] = None
        self.csv_exporter: Optional[CSVExporter] = None
        self.connected_client: Optional[AcuitySensorClient] = None
        self.laser_was_connected_before_collection = False
        self.sample_count = 0
        self.settings = QSettings("Acuity", "AS1100 Sensor Data Collector")
        self.output_folder = Path.home() / "sensor_data"
        
        # Create UI
        self._create_ui()
        self._refresh_ports()
        self._load_settings()
        self._on_mode_changed()  # Initialize UI state based on default mode
    
    def _create_ui(self) -> None:
        """Create GUI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel: controls
        left_panel = self._create_control_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel: data display
        right_panel = self._create_data_panel()
        main_layout.addWidget(right_panel, 1)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def _create_control_panel(self) -> QWidget:
        """Create left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Connection section
        conn_group = QGroupBox("Connection")
        conn_layout = QFormLayout(conn_group)
        
        self.port_combo = QComboBox()
        conn_layout.addRow("Port:", self.port_combo)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_ports)
        conn_layout.addRow(refresh_btn)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        conn_layout.addRow(self.connect_btn)
        
        self.status_label = QLabel("Disconnected")
        conn_layout.addRow("Status:", self.status_label)
        
        layout.addWidget(conn_group)
        
        # Laser control section
        laser_group = QGroupBox("Laser Control")
        laser_layout = QHBoxLayout(laser_group)
        
        self.laser_on_btn = QPushButton("Laser ON")
        self.laser_on_btn.setStyleSheet("background-color: #FFD700; font-weight: bold;")
        self.laser_on_btn.setEnabled(False)
        self.laser_on_btn.clicked.connect(self._on_laser_on)
        laser_layout.addWidget(self.laser_on_btn)
        
        self.laser_off_btn = QPushButton("Laser OFF")
        self.laser_off_btn.setStyleSheet("background-color: #A9A9A9; font-weight: bold;")
        self.laser_off_btn.setEnabled(False)
        self.laser_off_btn.clicked.connect(self._on_laser_off)
        laser_layout.addWidget(self.laser_off_btn)
        
        self.laser_distance_label = QLabel("Distance: -")
        laser_layout.addWidget(self.laser_distance_label)
        
        layout.addWidget(laser_group)
        
        # Measurement settings
        meas_group = QGroupBox("Measurement Settings")
        meas_layout = QFormLayout(meas_group)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Continuous", MeasurementMode.CONTINUOUS)
        self.mode_combo.addItem("Single", MeasurementMode.SINGLE)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        meas_layout.addRow("Mode:", self.mode_combo)
        
        # Frequency (only for continuous mode)
        self.freq_label = QLabel("Samples/Second:")
        self.freq_combo = QComboBox()
        for label, freq in self.FREQUENCY_PRESETS.items():
            self.freq_combo.addItem(label, freq)
        self.freq_combo.setCurrentIndex(3)  # Default 10
        meas_layout.addRow(self.freq_label, self.freq_combo)
        
        self.unit_combo = QComboBox()
        for unit in Unit:
            self.unit_combo.addItem(unit.value, unit)
        self.unit_combo.setCurrentIndex(0)  # Default mm
        meas_layout.addRow("Unit:", self.unit_combo)
        
        # Decimal places selector
        self.decimal_spinbox = QSpinBox()
        self.decimal_spinbox.setMinimum(1)
        self.decimal_spinbox.setMaximum(10)
        self.decimal_spinbox.setValue(4)
        meas_layout.addRow("Decimal Places:", self.decimal_spinbox)
        
        layout.addWidget(meas_group)
        
        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        
        self.export_csv_checkbox = QCheckBox("Export to CSV")
        self.export_csv_checkbox.setChecked(True)
        output_layout.addRow(self.export_csv_checkbox)
        
        self.folder_label = QLabel(str(self.output_folder))
        output_layout.addRow("Folder:", self.folder_label)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_folder)
        output_layout.addRow(browse_btn)
        
        layout.addWidget(output_group)
        
        # Collection control
        ctrl_group = QGroupBox("Collection")
        ctrl_layout = QVBoxLayout(ctrl_group)
        
        # Continuous mode buttons
        self.start_btn = QPushButton("Start Collection")
        self.start_btn.setStyleSheet("background-color: #90EE90; font-weight: bold;")
        self.start_btn.clicked.connect(self._on_start_collection)
        ctrl_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Collection")
        self.stop_btn.setStyleSheet("background-color: #FFB6C6; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_collection)
        ctrl_layout.addWidget(self.stop_btn)
        
        # Single mode button
        self.collect_btn = QPushButton("Collect")
        self.collect_btn.setStyleSheet("background-color: #87CEEB; font-weight: bold;")
        self.collect_btn.clicked.connect(self._on_collect_single)
        self.collect_btn.setVisible(False)
        ctrl_layout.addWidget(self.collect_btn)
        
        layout.addWidget(ctrl_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        return panel
    
    def _create_data_panel(self) -> QWidget:
        """Create right data display panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Sample table
        table_label = QLabel("Live Data:")
        layout.addWidget(table_label)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(6)
        self.data_table.setHorizontalHeaderLabels([
            "Timestamp", "Raw (0.1mm)", "Value", "Unit", "Mode", "Samples/Sec"
        ])
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSelectionMode(QAbstractItemView.SingleSelection)
        # Make columns auto-adjust to available width
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.data_table)
        
        # Status log
        log_label = QLabel("Status / Log:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        # Sample count
        self.count_label = QLabel("Samples: 0")
        layout.addWidget(self.count_label)
        
        # Export button
        self.open_folder_btn = QPushButton("Open Output Folder")
        self.open_folder_btn.clicked.connect(self._on_open_output_folder)
        layout.addWidget(self.open_folder_btn)
        
        return panel
    
    def _refresh_ports(self) -> None:
        """Refresh available serial ports."""
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        
        ports = AcuitySensorClient.list_ports()
        if ports:
            self.port_combo.addItems(ports)
            # Try to restore previous selection
            idx = self.port_combo.findText(current_port)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        else:
            self.port_combo.addItem("No ports found")
    
    @Slot()
    def _on_mode_changed(self) -> None:
        """Handle mode selection change."""
        mode = self.mode_combo.currentData()
        
        if mode == MeasurementMode.CONTINUOUS:
            # Show frequency controls
            self.freq_label.setVisible(True)
            self.freq_combo.setVisible(True)
            # Show continuous buttons
            self.start_btn.setVisible(True)
            self.stop_btn.setVisible(True)
            # Hide single button
            self.collect_btn.setVisible(False)
        else:  # Single mode
            # Hide frequency controls
            self.freq_label.setVisible(False)
            self.freq_combo.setVisible(False)
            # Hide continuous buttons
            self.start_btn.setVisible(False)
            self.stop_btn.setVisible(False)
            # Show single button
            self.collect_btn.setVisible(True)

        self._save_settings()
    
    @Slot()
    def _on_collect_single(self) -> None:
        """Handle single measurement collection."""
        port_string = self.port_combo.currentText()
        if not port_string or port_string == "No ports found":
            QMessageBox.warning(self, "Error", "Please select a valid port")
            return
        
        # Extract device name (handles "COM3" and "COM3 - Description" formats)
        port = AcuitySensorClient.get_port_device(port_string)
        
        # Create temporary client for single measurement
        # Use higher timeout for far-distance measurements
        client = AcuitySensorClient(port=port, sensor_id=0, timeout=3.0)
        
        try:
            if not client.connect():
                QMessageBox.critical(self, "Error", f"Failed to connect to {port}")
                return
            
            # Get single measurement
            response = client.get_single_measurement()
            
            if response:
                from app.sensor.parsing import parse_distance_response, is_error_response
                
                if is_error_response(response):
                    QMessageBox.warning(self, "Sensor Error", f"Sensor returned error: {response}")
                    self._log(f"Measurement error: {response}")
                else:
                    raw_value = parse_distance_response(response)
                    if raw_value is not None:
                        # Create sample record
                        from datetime import datetime
                        from app.domain.conversion import convert_0p1mm_to_unit
                        from app.domain.models import SampleRecord
                        
                        now = datetime.now()
                        unit = self.unit_combo.currentData()
                        converted_value = convert_0p1mm_to_unit(raw_value, unit)
                        
                        sample = SampleRecord(
                            timestamp_iso=now.isoformat(),
                            epoch_ms=int(now.timestamp() * 1000),
                            raw_0p1mm=raw_value,
                            value=converted_value,
                            unit=unit.value,
                            mode="single",
                            interval_hz=None,
                            sensor_id=0,
                            response=response,
                        )
                        
                        # Add to table
                        self._on_sample_acquired(sample)
                        
                        # Format with selected decimal places
                        decimal_places = self.decimal_spinbox.value()
                        formatted_value = f"{converted_value:.{decimal_places}f}"
                        self._log(f"Single measurement: {formatted_value} {unit.value}")
                    else:
                        QMessageBox.warning(self, "Parse Error", "Could not parse sensor response")
            else:
                QMessageBox.warning(self, "No Response", "No response from sensor")
                
        finally:
            client.disconnect()
    
    @Slot()
    def _on_connect_clicked(self) -> None:
        """Handle connect button click."""
        if self.connect_btn.text() == "Connect":
            port_string = self.port_combo.currentText()
            if not port_string or port_string == "No ports found":
                QMessageBox.warning(self, "Error", "Please select a valid port")
                return
            
            # Extract device name (handles "COM3" and "COM3 - Description" formats)
            port = AcuitySensorClient.get_port_device(port_string)
            
            # Try to connect with higher timeout for far-distance measurements
            client = AcuitySensorClient(
                port=port,
                sensor_id=0,
                timeout=3.0,
            )
            
            if client.connect():
                # connect() already verified the sensor responds (serial number check).
                # Read firmware separately to show in log.
                fw = client.read_firmware_version()
                
                # Store connected client for laser control
                self.connected_client = client
                
                self.status_label.setText(f"Connected ({port})")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.connect_btn.setText("Disconnect")
                self.laser_on_btn.setEnabled(True)
                self.laser_off_btn.setEnabled(True)
                
                # Parse and display serial number from connection verification
                sn = client.read_serial_number()
                info = f"Connected to {port}\n"
                if sn:
                    info += f"Serial: {sn}\n"
                if fw:
                    info += f"Firmware: {fw}\n"
                self._log(info)
            else:
                QMessageBox.critical(
                    self,
                    "Connection Failed",
                    f"Could not connect to sensor on {port}.\n\n"
                    "Please check:\n"
                    "  \u2022 The sensor is powered on\n"
                    "  \u2022 The USB cable is connected\n"
                    "  \u2022 The correct COM port is selected"
                )
        else:
            # Disconnect
            if self.connected_client:
                self.connected_client.disconnect()
                self.connected_client = None
            
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red;")
            self.connect_btn.setText("Connect")
            self.laser_on_btn.setEnabled(False)
            self.laser_off_btn.setEnabled(False)
            self.laser_distance_label.setText("Distance: -")
            self._log("Disconnected from sensor")
    
    @Slot()
    def _on_browse_folder(self) -> None:
        """Handle folder browse button click."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            str(self.output_folder),
        )
        
        if folder:
            self.output_folder = Path(folder)
            self.folder_label.setText(str(self.output_folder))
            self._save_settings()
            self._log(f"Output folder set to: {self.output_folder}")
    
    @Slot()
    def _on_start_collection(self) -> None:
        """Handle start collection button click."""
        port_string = self.port_combo.currentText()
        if not port_string or port_string == "No ports found":
            QMessageBox.warning(self, "Error", "Please select a valid port")
            return
        
        # Extract device name (handles "COM3" and "COM3 - Description" formats)
        port = AcuitySensorClient.get_port_device(port_string)
        
        if not self.output_folder.exists():
            self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Build config
        config = CollectionConfig(
            port=port,
            sensor_id=0,
            mode=self.mode_combo.currentData(),
            interval_mode=IntervalMode.HOST_THROTTLED,
            interval_hz=self.freq_combo.currentData(),
            unit=self.unit_combo.currentData(),
            output_folder=str(self.output_folder),
        )
        
        # Reset sample count and table
        self.sample_count = 0
        self.data_table.setRowCount(0)
        
        # Disconnect laser control to free up serial port for worker
        # We'll reconnect after collection stops
        laser_was_connected = False
        if self.connected_client and self.connected_client.is_connected():
            laser_was_connected = True
            self.connected_client.disconnect()
        
        # Create CSV exporter if enabled
        if self.export_csv_checkbox.isChecked():
            decimal_places = self.decimal_spinbox.value()
            self.csv_exporter = CSVExporter(str(self.output_folder), decimal_places=decimal_places)
            self.csv_exporter.open()
        else:
            self.csv_exporter = None
        
        # Start worker
        self.worker = AcquisitionWorker(config)
        self.worker.sample_acquired.connect(self._on_sample_acquired)
        self.worker.measurement_started.connect(self._on_measurement_started)
        self.worker.measurement_stopped.connect(self._on_measurement_stopped)
        self.worker.error_occurred.connect(self._on_error_occurred)
        
        # Store whether laser was connected so we can reconnect after
        self.laser_was_connected_before_collection = laser_was_connected
        
        self.worker.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.freq_combo.setEnabled(False)
        self.laser_on_btn.setEnabled(False)
        self.laser_off_btn.setEnabled(False)
        
        self._log("Collection started")
    
    @Slot()
    def _on_stop_collection(self) -> None:
        """Handle stop collection button click."""
        if self.worker:
            self.worker.stop()
        
        if self.csv_exporter:
            self.csv_exporter.close()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.freq_combo.setEnabled(True)
        
        # Reconnect laser control if it was connected before collection
        if hasattr(self, 'laser_was_connected_before_collection') and self.laser_was_connected_before_collection:
            port_string = self.port_combo.currentText()
            if port_string and port_string != "No ports found":
                port = AcuitySensorClient.get_port_device(port_string)
                import time
                time.sleep(0.5)  # Small delay to let port settle
                try:
                    self.connected_client = AcuitySensorClient(port=port, sensor_id=0, timeout=3.0)
                    if self.connected_client.connect():
                        self.laser_on_btn.setEnabled(True)
                        self.laser_off_btn.setEnabled(True)
                        self._log("Laser control reconnected")
                    else:
                        self._log("Warning: Could not reconnect laser control")
                        self.connected_client = None
                except Exception as e:
                    self._log(f"Error reconnecting laser: {str(e)}")
                    self.connected_client = None
            self.laser_was_connected_before_collection = False
        self.freq_combo.setEnabled(True)
        
        self._log("Collection stopped")
    
    @Slot()
    def _on_laser_on(self) -> None:
        """Handle laser on button click."""
        if not self.connected_client or not self.connected_client.is_connected():
            QMessageBox.warning(self, "Error", "Please connect to the sensor first")
            return

        try:
            response = self.connected_client.laser_on()
            if response:
                # Try to parse the distance from the response
                from app.sensor.parsing import parse_distance_response
                distance = parse_distance_response(response)
                if distance is not None:
                    unit = self.unit_combo.currentData()
                    from app.domain.conversion import convert_0p1mm_to_unit
                    converted = convert_0p1mm_to_unit(distance, unit)
                    decimal_places = self.decimal_spinbox.value()
                    formatted = f"{converted:.{decimal_places}f}"
                    self.laser_distance_label.setText(f"Distance: {formatted} {unit.value}")
                    self._log(f"✓ Laser ON - Distance: {formatted} {unit.value}")
                else:
                    self.laser_distance_label.setText("Distance: (no measurement)")
                    self._log(f"✓ Laser ON (Response: {response})")
            else:
                QMessageBox.warning(self, "Error", "No response from laser")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Laser ON failed: {str(e)}")
    
    @Slot()
    def _on_laser_off(self) -> None:
        """Handle laser off button click."""
        if not self.connected_client or not self.connected_client.is_connected():
            QMessageBox.warning(self, "Error", "Please connect to the sensor first")
            return

        try:
            response = self.connected_client.laser_off()
            if response is not None:
                self.laser_distance_label.setText("Distance: -")
                self._log(f"✓ Laser OFF")
            else:
                QMessageBox.warning(self, "Error", "No response from laser OFF")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Laser OFF failed: {str(e)}")
    
    @Slot(object)
    def _on_sample_acquired(self, sample) -> None:
        """Handle new sample acquired."""
        self.sample_count += 1
        
        # Get decimal places setting
        decimal_places = self.decimal_spinbox.value()
        
        # Add to table
        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        
        self.data_table.setItem(row, 0, QTableWidgetItem(sample.timestamp_iso[:19]))
        self.data_table.setItem(row, 1, QTableWidgetItem(str(sample.raw_0p1mm)))
        # Format with selected decimal places
        formatted_value = f"{sample.value:.{decimal_places}f}"
        self.data_table.setItem(row, 2, QTableWidgetItem(formatted_value))
        self.data_table.setItem(row, 3, QTableWidgetItem(sample.unit))
        self.data_table.setItem(row, 4, QTableWidgetItem(sample.mode))
        self.data_table.setItem(row, 5, QTableWidgetItem(
            str(sample.interval_hz) if sample.interval_hz else "-"
        ))
        
        # Scroll to latest
        self.data_table.scrollToBottom()
        
        # Update count
        self.count_label.setText(f"Samples: {self.sample_count}")
        
        # Write to CSV
        if self.csv_exporter:
            self.csv_exporter.write_sample(sample)
    
    @Slot(str)
    def _on_measurement_started(self, message: str) -> None:
        """Handle measurement started."""
        self._log(f"✓ {message}")
    
    @Slot(str)
    def _on_measurement_stopped(self, message: str) -> None:
        """Handle measurement stopped."""
        self._log(f"✓ {message}")
    
    @Slot(str)
    def _on_error_occurred(self, message: str) -> None:
        """Handle error."""
        self._log(f"✗ ERROR: {message}")
        QMessageBox.critical(self, "Error", message)
        self._on_stop_collection()
    
    @Slot()
    def _on_open_output_folder(self) -> None:
        """Open the currently selected output folder."""
        try:
            self.output_folder.mkdir(parents=True, exist_ok=True)

            import subprocess
            import platform

            if platform.system() == "Windows":
                import os
                os.startfile(str(self.output_folder))
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(self.output_folder)])
            else:
                subprocess.Popen(["xdg-open", str(self.output_folder)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open folder: {str(e)}")

    def _load_settings(self) -> None:
        """Load persisted user settings into the UI."""
        output_folder = self.settings.value("output_folder", str(self.output_folder), type=str)
        self.output_folder = Path(output_folder)
        self.folder_label.setText(str(self.output_folder))

        export_csv = self.settings.value("export_csv", True, type=bool)
        self.export_csv_checkbox.setChecked(export_csv)

        decimal_places = self.settings.value("decimal_places", 4, type=int)
        self.decimal_spinbox.setValue(decimal_places)

        saved_mode = self.settings.value("mode", MeasurementMode.CONTINUOUS.value, type=str)
        for i in range(self.mode_combo.count()):
            mode = self.mode_combo.itemData(i)
            if mode and mode.value == saved_mode:
                self.mode_combo.setCurrentIndex(i)
                break

        saved_freq = self.settings.value("frequency_hz", 10.0, type=float)
        for i in range(self.freq_combo.count()):
            freq = self.freq_combo.itemData(i)
            if freq == saved_freq:
                self.freq_combo.setCurrentIndex(i)
                break

        saved_unit = self.settings.value("unit", Unit.MM.value, type=str)
        for i in range(self.unit_combo.count()):
            unit = self.unit_combo.itemData(i)
            if unit and unit.value == saved_unit:
                self.unit_combo.setCurrentIndex(i)
                break

        saved_port = self.settings.value("port", "", type=str)
        if saved_port:
            idx = self.port_combo.findText(saved_port)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)

        self.port_combo.currentIndexChanged.connect(self._save_settings)
        self.mode_combo.currentIndexChanged.connect(self._save_settings)
        self.freq_combo.currentIndexChanged.connect(self._save_settings)
        self.unit_combo.currentIndexChanged.connect(self._save_settings)
        self.decimal_spinbox.valueChanged.connect(self._save_settings)
        self.export_csv_checkbox.toggled.connect(self._save_settings)

    def _save_settings(self, *args) -> None:
        """Persist current user settings."""
        self.settings.setValue("output_folder", str(self.output_folder))
        self.settings.setValue("export_csv", self.export_csv_checkbox.isChecked())
        self.settings.setValue("decimal_places", self.decimal_spinbox.value())

        mode = self.mode_combo.currentData()
        if mode is not None:
            self.settings.setValue("mode", mode.value)

        unit = self.unit_combo.currentData()
        if unit is not None:
            self.settings.setValue("unit", unit.value)

        freq = self.freq_combo.currentData()
        if freq is not None:
            self.settings.setValue("frequency_hz", float(freq))

        port_text = self.port_combo.currentText()
        if port_text and port_text != "No ports found":
            self.settings.setValue("port", port_text)

        self.settings.sync()

    def closeEvent(self, event) -> None:
        """Persist settings when the window closes."""
        self._save_settings()
        super().closeEvent(event)
    
    def _log(self, message: str) -> None:
        """Add message to log."""
        self.log_text.append(message)
        self.statusBar.showMessage(message)
