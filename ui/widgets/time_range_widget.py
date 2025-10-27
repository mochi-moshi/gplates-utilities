"""
Time Range Widget

A widget for entering and validating geological time ranges with validation feedback.
"""

from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QLabel, QLayout


class TimeRangeWidget(QWidget):
    """Widget for entering geological time ranges with validation."""

    timeChanged = pyqtSignal(float, float)  # start_time, end_time

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI components."""
        layout = QFormLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        # Time inputs with validators
        self.start_time = QLineEdit()
        self.start_time.setValidator(QDoubleValidator())
        self.start_time.setPlaceholderText("e.g., 100.0")

        self.end_time = QLineEdit()
        self.end_time.setValidator(QDoubleValidator())
        self.end_time.setPlaceholderText("e.g., 50.0")

        # Connect signals with delay to avoid rapid updates
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate_times)

        self.start_time.textChanged.connect(lambda: self.validation_timer.start(500))
        self.end_time.textChanged.connect(lambda: self.validation_timer.start(500))

        layout.addRow("Start/Older Time (Mya):", self.start_time)
        layout.addRow("End/Newer Time (Mya):", self.end_time)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 11px;")
        layout.addRow(self.status_label)
        self.status_label.setDisabled(True)

        self.setLayout(layout)
        self.setMinimumSize(layout.minimumSize())

    def validate_times(self):
        """Validate time range and emit signal if valid."""
        if self._updating:
            return False

        if self._validate_times():
            self._updating = True
            try:
                start = float(self.start_time.text())
                end = float(self.end_time.text())
                self.timeChanged.emit(start, end)
                return True
            finally:
                self._updating = False
        return False

    def _validate_times(self):
        """Validate time range"""
        try:
            start = float(self.start_time.text()) if self.start_time.text() else None
            end = float(self.end_time.text()) if self.end_time.text() else None

            if start is not None and end is not None:
                if start <= end:
                    self.status_label.setText(
                        "⚠️ Start time should be greater than end time"
                    )
                    self.status_label.setStyleSheet("color: orange; font-size: 11px;")
                    self.status_label.setDisabled(False)
                    return False
                else:
                    duration = start - end
                    self.status_label.setText(
                        f"✓ Duration: {duration:.1f} million years"
                    )
                    self.status_label.setStyleSheet("color: green; font-size: 11px;")
                    self.status_label.setDisabled(False)
                    return True
            else:
                self.status_label.setText("Enter both start and end times")
                self.status_label.setStyleSheet("font-size: 11px;")
                self.status_label.setDisabled(False)

        except ValueError:
            self.status_label.setText("⚠️ Please enter valid numbers")
            self.status_label.setStyleSheet("color: red; font-size: 11px;")
            self.status_label.setDisabled(False)

        return False

    def get_times(self) -> tuple[float, float]:
        """Get validated time range."""
        if self._validate_times():
            return float(self.start_time.text()), float(self.end_time.text())
        raise ValueError("Invalid time range")

    def set_times(self, start_time: float, end_time: float):
        """Set time range values."""
        self._updating = True
        try:
            self.start_time.setText(str(start_time))
            self.end_time.setText(str(end_time))
            self._validate_times()
        finally:
            self._updating = False
