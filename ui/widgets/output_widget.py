"""
Output Widget

A reusable widget for handling file output with common options like append and topology generation.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QCheckBox, QFileDialog, QLabel
)
from core.session import Session


class OutputWidget(QWidget):
    """Widget for handling file output options."""
    
    pathChange = pyqtSignal(str)
    
    def __init__(self, session: Session, file_filter: str = "GPlates Markup Language (*.gpml)", 
                 enable_topology_generation: bool = True, parent=None):
        super().__init__(parent)
        self.session = session
        self.file_filter = file_filter
        self.enable_topology_generation = enable_topology_generation
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # File path selection
        file_layout = QFormLayout()
        
        path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        self.output_path.setPlaceholderText("Select output file location...")
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.select_output_path)
        
        path_layout.addWidget(self.output_path, 1)
        path_layout.addWidget(self.browse_button)
        
        file_layout.addRow("Output File:", path_layout)
        
        # Output options
        options_layout = QVBoxLayout()
        
        self.append_to_file = QCheckBox("Append to existing file")
        self.append_to_file.setToolTip("If checked, results will be added to existing file instead of overwriting it")
        options_layout.addWidget(self.append_to_file)
        
        # Only show topology generation option if enabled
        if self.enable_topology_generation:
            self.generate_topologies = QCheckBox("Generate topologies")
            self.generate_topologies.setDisabled(True)
            self.generate_topologies.setToolTip("Generate topological features for the processed results")
            options_layout.addWidget(self.generate_topologies)
        else:
            self.generate_topologies = None
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        
        layout.addLayout(file_layout)
        layout.addLayout(options_layout)
        layout.addWidget(self.status_label)
        
    def select_output_path(self):
        """Open file dialog to select output path."""
        initial_path = self.session._project_path if self.session._project_path else "."
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Select Output File", 
            initial_path,
            self.file_filter
        )
        
        if file_path:
            self.output_path.setText(file_path)
            self.status_label.setText("✓ Output path selected")
            self.status_label.setStyleSheet("color: green; font-size: 11px;")
            self.pathChange.emit(file_path)
        else:
            self.status_label.setText("Please select an output file")
            self.status_label.setStyleSheet("color: #666; font-size: 11px;")
            self.pathChange.emit('')
    
    def get_output_path(self) -> str:
        """Get the selected output path."""
        return self.output_path.text()
    
    def set_output_path(self, path: str):
        """Set the output path."""
        self.output_path.setText(path)
        if path:
            self.status_label.setText("✓ Output path set")
            self.status_label.setStyleSheet("color: green; font-size: 11px;")
    
    def should_append(self) -> bool:
        """Check if should append to existing file."""
        return self.append_to_file.isChecked()
    
    def should_generate_topologies(self) -> bool:
        """Check if should generate topologies."""
        if self.generate_topologies is not None:
            return self.generate_topologies.isChecked()
        return False  # Return False if topology generation is disabled
    
    def is_valid(self) -> tuple[bool, str]:
        """Validate the output configuration."""
        if not self.output_path.text():
            return False, "No output file selected"
        return True, "Output configuration is valid"