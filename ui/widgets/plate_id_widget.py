"""
Plate ID Widget

A widget for entering and validating plate IDs with optional uniqueness validation.
"""

from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QFormLayout, QSpinBox, QLabel, QCheckBox, QVBoxLayout
from core.session import Session

class PlateIdWidget(QWidget):
    """Widget for entering plate IDs with validation."""
    
    plateIdChanged = Signal(int)  # plate_id
    
    def __init__(self, session: Session, label: str = "Plate ID", 
                 enable_uniqueness_validation: bool = True, parent=None):
        super().__init__(parent)
        self.label = label
        self.session = session
        self.enable_uniqueness_validation = enable_uniqueness_validation
        self._updating = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QFormLayout(self)
        
        # Plate ID input
        self.plate_id_input = QSpinBox()
        self.plate_id_input.setRange(1, 9999)
        
        # Connect signals with delay to avoid rapid validation
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate_plate_id)
        
        self.plate_id_input.valueChanged.connect(lambda: self.validation_timer.start(300))
        
        layout.addRow(f"{self.label}:", self.plate_id_input)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addRow(self.status_label)
        
        # Initial validation
        self.validate_plate_id()
        
    def validate_plate_id(self):
        """Validate plate ID and emit signal if valid."""
        if self._updating:
            return False
            
        plate_id = self.plate_id_input.value()
        is_valid = self._validate_plate_id(plate_id)
        
        if is_valid:
            self._updating = True
            try:
                self.plateIdChanged.emit(plate_id)
                return True
            finally:
                self._updating = False
        return False
    
    def _validate_plate_id(self, plate_id: int) -> bool:
        """Validate plate ID against rotation model if uniqueness checking is enabled."""
        try:
            # Basic validation - plate ID must be positive
            if plate_id <= 0:
                self.status_label.setText("⚠️ Plate ID must be positive")
                self.status_label.setStyleSheet("color: red; font-size: 11px;")
                self._set_input_error_style(True)
                return False
            
            # Uniqueness validation (if enabled and rotation features available)
            if (self.enable_uniqueness_validation and self.session._rotationFeatureCollection is not None):
                
                # Check if plate ID already exists in rotation model
                for rotation_feature in self.session._rotationFeatureCollection:
                    try:
                        fixed_id, moving_id, samples = rotation_feature.get_total_reconstruction_pole()
                        if moving_id == plate_id:
                            self.status_label.setText(f"⚠️ Plate ID {plate_id} already exists in rotation model")
                            self.status_label.setStyleSheet("color: red; font-size: 11px;")
                            self._set_input_error_style(True)
                            return False
                    except Exception:
                        # If we can't read this rotation feature, skip it
                        continue
                
                # Valid and unique
                self.status_label.setText(f"✓ Plate ID {plate_id} is valid and unique")
                self.status_label.setStyleSheet("color: green; font-size: 11px;")
                self._set_input_error_style(False)
                return True
            else:
                # Valid but not checking uniqueness
                self.status_label.setText(f"✓ Plate ID {plate_id} is valid")
                self.status_label.setStyleSheet("color: green; font-size: 11px;")
                self._set_input_error_style(False)
                return True
                
        except Exception:
            self.status_label.setText("⚠️ Error validating plate ID")
            self.status_label.setStyleSheet("color: red; font-size: 11px;")
            self._set_input_error_style(True)
            return False
    
    def _set_input_error_style(self, is_error: bool):
        """Set error styling on the input field."""
        if is_error:
            self.plate_id_input.setStyleSheet("""
                QSpinBox {
                    border: 2px solid red;
                    background-color: #fff5f5;
                }
            """)
        else:
            self.plate_id_input.setStyleSheet("")
    
    def get_plate_id(self) -> int:
        """Get validated plate ID."""
        plate_id = self.plate_id_input.value()
        if self._validate_plate_id(plate_id):
            return plate_id
        raise ValueError("Invalid plate ID")
    
    def set_plate_id(self, plate_id: int):
        """Set plate ID value."""
        self._updating = True
        try:
            self.plate_id_input.setValue(plate_id)
            self._validate_plate_id(plate_id)
        finally:
            self._updating = False
    
    def is_valid(self) -> bool:
        """Check if current plate ID is valid."""
        return self._validate_plate_id(self.plate_id_input.value())


class DualPlateIdWidget(QWidget):
    """Widget for entering left and right plate IDs for rifting operations."""
    
    plateIdsChanged = Signal(int, int)  # left_plate_id, right_plate_id
    
    def __init__(self, session: Session, 
                 enable_uniqueness_validation: bool = True, parent=None):
        super().__init__(parent)
        self.enable_uniqueness_validation = enable_uniqueness_validation
        self.setup_ui(session)
        
    def setup_ui(self, session: Session):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Description
        description_label = QLabel("Features split by the rift will be assigned to left or right plates based on their position relative to the rift line:")
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #666; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(description_label)
        
        # Left plate ID widget
        self.left_plate_widget = PlateIdWidget(session, "Left Plate ID", self.enable_uniqueness_validation)
        self.left_plate_widget.plateIdChanged.connect(self._emit_plate_ids_changed)
        layout.addWidget(self.left_plate_widget)
        
        # Right plate ID widget  
        self.right_plate_widget = PlateIdWidget(session, "Right Plate ID", self.enable_uniqueness_validation)
        self.right_plate_widget.plateIdChanged.connect(self._emit_plate_ids_changed)
        layout.addWidget(self.right_plate_widget)
    
    def _emit_plate_ids_changed(self):
        """Emit signal when either plate ID changes and both are valid."""
        if self.left_plate_widget.is_valid() and self.right_plate_widget.is_valid():
            left_id = self.left_plate_widget.get_plate_id()
            right_id = self.right_plate_widget.get_plate_id()
            self.plateIdsChanged.emit(left_id, right_id)
    
    def get_plate_ids(self) -> tuple[int, int]:
        """Get validated plate IDs."""
        return self.left_plate_widget.get_plate_id(), self.right_plate_widget.get_plate_id()
    
    def set_plate_ids(self, left_id: int, right_id: int):
        """Set plate ID values."""
        self.left_plate_widget.set_plate_id(left_id)
        self.right_plate_widget.set_plate_id(right_id)
    
    def is_valid(self) -> bool:
        """Check if both plate IDs are valid."""
        return self.left_plate_widget.is_valid() and self.right_plate_widget.is_valid()