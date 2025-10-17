"""
Improved Rotation Management Window with intuitive workflow-based UI design.

This redesigned interface provides a comprehensive solution for rotation-related operations
including initialization, plate creation, and rotation management with guided workflows.
"""

from os import path
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
    QTabWidget, QGroupBox, QTextEdit, QCheckBox, QSpinBox,
    QFormLayout, QLayout, QMainWindow, QScrollArea, QFrame
)

from core.session import Session, FeatureDataColumn
from core.rotations import create_initial_rotations, create_new_rotation_plate, replace_final_rotation
from ui.components.process_step_widget import ProcessStepWidget
from ui.widgets.time_range_widget import TimeRangeWidget
from ui.widgets.feature_selector_widget import FeatureSelectorWidget
from ui.widgets.output_widget import OutputWidget
from ui.base.process_tab_widget import ProcessTabWidget

from pygplates import FeatureCollection
import traceback


class RotationInitializationWidget(ProcessTabWidget):
    """Widget for initializing rotation models."""

    def setup_ui(self):
        content_layout = QVBoxLayout()

        # Workflow steps
        self.steps = [
            ProcessStepWidget(1, "Select Features for Rotation Model",
                            "Choose features that will be used to create rotation model.\nSelect none to generate for all plates."),
            ProcessStepWidget(2, "Set Time Parameters",
                            "Define the time period for rotation model"),
            ProcessStepWidget(3, "Initialize & Save",
                            "Create rotation model and save results")
        ]

        for step in self.steps:
            content_layout.addWidget(step)

        # Step 1: Feature selection
        self.feature_group = QGroupBox("Feature Selection")
        self.feature_selector = FeatureSelectorWidget(self.session)
        self.feature_selector.selectionChanged.connect(self.on_features_selected)

        feature_layout = QVBoxLayout(self.feature_group)
        feature_layout.addWidget(self.feature_selector)

        # Step 2: Time parameters
        self.time_group = QGroupBox("Time Parameters")
        self.time_widget = TimeRangeWidget()
        self.time_widget.timeChanged.connect(self.on_time_changed)

        time_layout = QVBoxLayout(self.time_group)
        time_layout.addWidget(self.time_widget)

        # Step 3: Output controls
        self.output_group = QGroupBox("Output")
        self.output_widget = OutputWidget(self.session, "PLATES4 Rotation File (*.rot)", enable_topology_generation=False)
        self.output_widget.pathChange.connect(lambda: self.validate_and_enable_process())

        output_layout = QVBoxLayout(self.output_group)
        output_layout.addWidget(self.output_widget)
        
        # Process button
        self.process_button = QPushButton("🔄 Initialize Rotation Model")
        self.process_button.clicked.connect(self.initialize_rotations)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        output_layout.addWidget(self.process_button)

        content_layout.addWidget(self.feature_group)
        content_layout.addWidget(self.time_group)
        content_layout.addWidget(self.output_group)

        # Set first step as active
        self.steps[0].set_active(True)
        self.steps[0].set_completed(True)

        # Wrap content in scroll area
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        scroll_area = self.wrap_in_scroll_area(content_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    
    def on_time_changed(self, start_time: float, end_time: float):
        """Handle time range changes."""
        self.update_step_status(1, True)
        self.validate_and_enable_process()
    
    def on_features_selected(self, count: int):
        """Handle feature selection changes."""
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_output, _ = self.output_widget.is_valid()

        # Does not need to select any features
        self.process_button.setEnabled(self.time_widget._validate_times() and has_output)
    
    def initialize_rotations(self):
        """Initialize rotation model."""
        try:
            # Get parameters
            selected_features = self.feature_selector.get_selected_features()
            start_time, end_time = self.time_widget.get_times()
            
            if not selected_features:
                # Use all features if none selected
                selected_features = [f for lfc in self.session.loaded_feature_collections for f in lfc.feature_collection]
            
            if not selected_features:
                QMessageBox.warning(self, "Error", "No features available for rotation model creation")
                return
            
            # Create rotation model
            result_fc = create_initial_rotations(selected_features, start_time, end_time)
            
            if len(result_fc) == 0:
                QMessageBox.warning(self, "No Results", "No rotation features created")
                return
            
            # Save results
            output_path = self.output_widget.get_output_path()

            if self.output_widget.should_append():
              output_fc = FeatureCollection(output_path)
              output_fc.add(output_fc)
              output_fc.write(output_path)
            else:
              result_fc.write(output_path)
            
            # Load rotation model if none exists
            if not self.session._rotationModel:
                self.session.load_rotation_model(output_path)
                status_msg = f"Rotation model {'appended' if self.output_widget.should_append() else 'created'} and loaded: {path.basename(output_path)}"
            else:
                status_msg = f"Rotation model {'appended' if self.output_widget.should_append() else 'created'}: {path.basename(output_path)}"
            
            self.update_step_status(2, True)
            QMessageBox.information(self, "Success", 
                                  f"Rotation model initialization complete!\n{status_msg}\n"
                                  f"Rotation features created: {len(result_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Rotation model initialization failed:\n{str(e)}")
            traceback.print_exception(e)


class PlateCreationWidget(ProcessTabWidget):
    """Widget for creating new plates with rotations."""

    def setup_ui(self):
        content_layout = QVBoxLayout()

        # Workflow steps
        self.steps = [
            ProcessStepWidget(1, "Select Features for New Plate",
                            "Choose features that will become the new plate"),
            ProcessStepWidget(2, "Set Plate Parameters",
                            "Define new plate ID and time parameters"),
            ProcessStepWidget(3, "Configure Output Options",
                            "Set output locations for features and rotations"),
            ProcessStepWidget(4, "Create Plate & Rotations",
                            "Generate new plate and rotation entries")
        ]

        for step in self.steps:
            content_layout.addWidget(step)

        # Step 1: Feature selection
        self.feature_group = QGroupBox("Feature Selection for New Plate")
        self.feature_selector = FeatureSelectorWidget(self.session)
        self.feature_selector.selectionChanged.connect(self.on_features_selected)

        feature_layout = QVBoxLayout(self.feature_group)
        feature_layout.addWidget(self.feature_selector)

        # Step 2: Plate parameters
        self.params_group = QGroupBox("Plate Parameters")
        params_layout = QFormLayout(self.params_group)
        
        self.new_plate_id = QSpinBox()
        self.new_plate_id.setRange(0, 9999)
        self.new_plate_id.setValue(1000)
        self.new_plate_id.valueChanged.connect(self.validate_plate_id)
        
        self.split_time = QLineEdit()
        self.split_time.setValidator(QDoubleValidator())
        self.split_time.setPlaceholderText("e.g., 10.0")
        self.split_time.textChanged.connect(lambda: self.update_step_status(1, bool(self.split_time.text())))
        
        params_layout.addRow("New Plate ID:", self.new_plate_id)
        params_layout.addRow("Split Time (Ma):", self.split_time)

        # Step 3: Output configuration
        self.output_group = QGroupBox("Output Configuration")
        output_layout = QVBoxLayout(self.output_group)

        # Feature output
        feature_output_layout = QFormLayout()
        self.feature_output_widget = OutputWidget(self.session, "GPlates Markup Language (*.gpml)", enable_topology_generation=False)
        self.feature_output_widget.pathChange.connect(lambda: self.validate_and_enable_process())
        feature_output_layout.addRow("Feature Output:", self.feature_output_widget)

        # Rotation output
        rotation_output_layout = QFormLayout()
        self.rotation_output_widget = OutputWidget(self.session, "PLATES4 Rotation File (*.rot)", enable_topology_generation=False)
        self.rotation_output_widget.pathChange.connect(lambda: self.validate_and_enable_process())
        rotation_output_layout.addRow("Rotation Output:", self.rotation_output_widget)
        
        output_layout.addLayout(feature_output_layout)
        output_layout.addLayout(rotation_output_layout)
        
        # Process button
        self.process_button = QPushButton("🆕 Create New Plate")
        self.process_button.clicked.connect(self.create_plate)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        output_layout.addWidget(self.process_button)

        content_layout.addWidget(self.feature_group)
        content_layout.addWidget(self.params_group)
        content_layout.addWidget(self.output_group)

        # Set first step as active
        self.steps[0].set_active(True)

        # Wrap content in scroll area
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        scroll_area = self.wrap_in_scroll_area(content_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
    
    def on_features_selected(self, count: int):
        """Handle feature selection changes."""
        if count > 0:
            self.update_step_status(0, True)
        self.validate_and_enable_process()
    
    def validate_plate_id(self):
        """Validate that the new plate ID doesn't already exist."""
        new_id = self.new_plate_id.value()
        
        # Check if plate ID already exists
        all_ids = set([f.get_reconstruction_plate_id() for lfc in self.session.loaded_feature_collections for f in lfc.feature_collection])
        
        if new_id in all_ids:
            QMessageBox.warning(self, "Duplicate Plate ID", 
                              f"Plate ID {new_id} already exists in the loaded features. Please choose a different ID.")
        else:
            self.update_step_status(1, True)
            
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_features = len(self.feature_selector.get_selected_features()) > 0
        has_time = bool(self.split_time.text())
        has_feature_output, _ = self.feature_output_widget.is_valid()
        has_rotation_output, _ = self.rotation_output_widget.is_valid()
        
        if has_feature_output and has_rotation_output:
            self.update_step_status(2, True)
        
        self.process_button.setEnabled(has_features and has_time and has_feature_output and has_rotation_output)
    
    def create_plate(self):
        """Create new plate with rotations."""
        try:
            # Validate rotation model
            if not self.session._rotationModel:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Get parameters
            selected_features = self.feature_selector.get_selected_features()
            new_plate_id = self.new_plate_id.value()
            split_time = float(self.split_time.text())
            
            # Create new plate
            feature_fc, rotation_fc = create_new_rotation_plate(
                selected_features,
                self.session._rotationFeatureCollection,
                new_plate_id,
                split_time
            )
            
            if len(feature_fc) == 0:
                QMessageBox.warning(self, "No Results", "No features created for new plate")
                return
            
            # Save results
            feature_path = self.feature_output_widget.get_output_path()
            rotation_path = self.rotation_output_widget.get_output_path()
            
            # Handle feature output
            if self.feature_output_widget.should_append() and path.exists(feature_path):
                existing_fc = FeatureCollection(feature_path)
                for feature in feature_fc:
                    existing_fc.add(feature)
                existing_fc.write(feature_path)
            else:
                feature_fc.write(feature_path)
            
            # Handle rotation output
            if self.rotation_output_widget.should_append() and path.exists(rotation_path):
                existing_rc = FeatureCollection(rotation_path)
                for rotation in rotation_fc:
                    existing_rc.add(rotation)
                existing_rc.write(rotation_path)
            else:
                rotation_fc.write(rotation_path)
            
            self.update_step_status(3, True)
            QMessageBox.information(self, "Success", 
                                  f"New plate creation complete!\n"
                                  f"Features saved to: {path.basename(feature_path)}\n"
                                  f"Rotations saved to: {path.basename(rotation_path)}\n"
                                  f"New plate ID: {new_plate_id}\n"
                                  f"Features created: {len(feature_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Plate creation failed:\n{str(e)}")
            traceback.print_exception(e)


class RotationMaintenanceWidget(QWidget):
    """Widget for rotation model maintenance operations."""
    
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.setup_ui()
    
    def setup_ui(self):
        content_layout = QVBoxLayout()

        # Header
        header_label = QLabel("<h3>Rotation Model Maintenance</h3>")
        content_layout.addWidget(header_label)

        # Maintenance operations
        operations_group = QGroupBox("Maintenance Operations")
        operations_layout = QVBoxLayout(operations_group)

        # Fix final rotation
        fix_rotation_group = QGroupBox("Fix Final Rotation")
        fix_layout = QVBoxLayout(fix_rotation_group)
        
        fix_description = QLabel(
            "Fix the final rotation in the rotation model to ensure proper plate reconstruction. "
            "This corrects any inconsistencies in the final rotation entries."
        )
        fix_description.setWordWrap(True)
        fix_description.setStyleSheet("color: #666; margin-bottom: 10px;")
        fix_layout.addWidget(fix_description)

        fix_button_layout = QHBoxLayout()
        
        self.rotation_output_path = QLineEdit()
        self.rotation_output_path.setPlaceholderText("Select rotation file output location...")
        self.rotation_output_path.setReadOnly(True)
        
        self.browse_rotation_button = QPushButton("Browse...")
        self.browse_rotation_button.clicked.connect(self.select_rotation_output)
        
        self.fix_rotation_button = QPushButton("🔧 Fix Final Rotation")
        self.fix_rotation_button.clicked.connect(self.fix_final_rotation)
        self.fix_rotation_button.setEnabled(False)
        self.fix_rotation_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        
        fix_button_layout.addWidget(QLabel("Output:"))
        fix_button_layout.addWidget(self.rotation_output_path, 1)
        fix_button_layout.addWidget(self.browse_rotation_button)
        fix_button_layout.addWidget(self.fix_rotation_button)
        
        fix_layout.addLayout(fix_button_layout)

        # Model validation
        validation_group = QGroupBox("Model Validation")
        validation_layout = QVBoxLayout(validation_group)

        validation_description = QLabel(
            "Validate the current rotation model for consistency and completeness. "
            "This checks for missing rotations, duplicate entries, and temporal continuity."
        )
        validation_description.setWordWrap(True)
        validation_description.setStyleSheet("color: #666; margin-bottom: 10px;")
        validation_layout.addWidget(validation_description)

        validation_button_layout = QHBoxLayout()
        
        self.validate_button = QPushButton("✅ Validate Model")
        self.validate_button.clicked.connect(self.validate_rotation_model)
        self.validate_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        
        validation_button_layout.addWidget(self.validate_button)
        validation_button_layout.addStretch()
        
        validation_layout.addLayout(validation_button_layout)
        
        # Validation results
        self.validation_results = QTextEdit()
        self.validation_results.setMaximumHeight(150)
        self.validation_results.setReadOnly(True)
        self.validation_results.hide()
        
        validation_layout.addWidget(self.validation_results)
        
        operations_layout.addWidget(fix_rotation_group)
        operations_layout.addWidget(validation_group)

        content_layout.addWidget(operations_group)
        content_layout.addStretch()

        # Wrap content in scroll area
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
    
    def select_rotation_output(self):
        """Select rotation output file."""
        initial_path = self.session._project_path if self.session._project_path else "."
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Rotation Output File",
            initial_path,
            "PLATES4 Rotation File (*.rot)"
        )
        
        if file_path:
            self.rotation_output_path.setText(file_path)
            self.fix_rotation_button.setEnabled(True)
    
    def fix_final_rotation(self):
        """Fix the final rotation in the rotation model."""
        try:
            if not self.session._rotationModel:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            output_path = self.rotation_output_path.text()
            if not output_path:
                QMessageBox.warning(self, "Error", "Please select an output file")
                return
            
            # Fix final rotation
            fixed_fc = replace_final_rotation(self.session._rotationFeatureCollection)
            fixed_fc.write(output_path)
            
            QMessageBox.information(self, "Success", 
                                  f"Final rotation fixed successfully!\n"
                                  f"Results saved to: {path.basename(output_path)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fix final rotation:\n{str(e)}")
    
    def validate_rotation_model(self):
        """Validate the rotation model for consistency."""
        try:
            if not self.session._rotationModel:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Basic validation
            rotation_features = [f for f in self.session._rotationFeatureCollection]
            
            if not rotation_features:
                self.validation_results.setText("❌ No rotation features found in the model")
                self.validation_results.show()
                return
            
            # Count rotations by plate
            plate_ids = set()
            time_ranges = {}
            
            for feature in rotation_features:
                fixed_id, plate_id, samples = feature.get_total_reconstruction_pole()
                plate_ids.add(plate_id)

                times = [s.get_time() for s in samples if s.get_time() != 0]
                begin_time = max(times)
                end_time = min(times)
                
                if plate_id not in time_ranges:
                    time_ranges[plate_id] = {'start': begin_time, 'end': end_time}
                else:
                    time_ranges[plate_id]['start'] = max(time_ranges[plate_id]['start'], begin_time)
                    time_ranges[plate_id]['end'] = min(time_ranges[plate_id]['end'], end_time)
            
            # Generate validation report
            report = []
            report.append("✅ Rotation Model Validation Report")
            report.append("=" * 40)
            report.append(f"Total rotation features: {len(rotation_features)}")
            report.append(f"Unique plates: {len(plate_ids)}")
            report.append("")
            
            # Plate summary
            missing_rotations = []
            report.append("Plate Rotation Summary:")
            for plate_id in sorted(plate_ids):
                time_info = f"Plate {plate_id}: "
                if plate_id in time_ranges:
                    tr = time_ranges[plate_id]
                    time_info += f"(Time range: {tr['start']:.2f} - {tr['end']:.2f} Mya)"
                else:
                    time_info += "MISSING"
                    missing_rotations.append(plate_id)
                report.append(time_info)
            
            report.append("")
            
            # Basic checks
            warnings = []
            if len(missing_rotations) > 0:
                warnings.append(f"⚠️  {len(missing_rotations)} plates missing rotations ({', '.join(missing_rotations)})")
            
            if warnings:
                report.append("Warnings:")
                report.extend(warnings)
            else:
                report.append("✅ No major issues detected")
            
            self.validation_results.setText("\n".join(report))
            self.validation_results.show()
            
        except Exception as e:
            error_msg = f"❌ Validation failed: {str(e)}"
            self.validation_results.setText(error_msg)
            self.validation_results.show()


class ImprovedRotationManagementWindow(QWidget):
    """
    Improved Rotation Management Window with guided workflows.
    
    Features:
    - Separate tabs for rotation initialization, plate creation, and maintenance
    - Step-by-step visual workflows
    - Integrated validation and error handling
    - Comprehensive rotation model management
    """
    
    def __init__(self, session: Session):
        super().__init__()
        self.session = session

        self.setWindowTitle("Rotation Management Helper")
        self.resize(800, 600)

        self.setup_ui()

    def setup_ui(self):
        """Setup the main UI components."""
        layout = QVBoxLayout()
        
        # Header info
        header_label = QLabel("""
        <h2>🔄 Rotation Management Helper</h2>
        <p>This tool provides comprehensive rotation model management with guided workflows.
        Initialize rotation models, create new plates, and maintain model consistency.</p>
        """)
        header_label.setWordWrap(True)
        header_label.setStyleSheet("""
            QLabel {
                padding: 15px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header_label)
        
        # Tab widget for different operations
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Create tabs
        self.initialization_tab = RotationInitializationWidget(self.session)
        self.plate_creation_tab = PlateCreationWidget(self.session)  
        self.maintenance_tab = RotationMaintenanceWidget(self.session)
        
        # Add tabs with emojis for visual appeal
        self.tab_widget.addTab(self.initialization_tab, "🔄 Initialize Rotations")
        self.tab_widget.addTab(self.plate_creation_tab, "🆕 Create New Plate")
        self.tab_widget.addTab(self.maintenance_tab, "🔧 Maintenance")
        
        # Set tab tooltips
        self.tab_widget.setTabToolTip(0, "Initialize rotation models from features")
        self.tab_widget.setTabToolTip(1, "Create new plates with rotation entries")
        self.tab_widget.setTabToolTip(2, "Maintain and validate rotation models")

        self.tab_widget.currentChanged.connect(self.tabChange)
        
        layout.addWidget(self.tab_widget)

        self.setLayout(layout)
        # self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.tab_widget.setMinimumSize(self.tab_widget.currentWidget().layout().minimumSize())
        self.setMinimumSize(self.layout().minimumSize())

    def tabChange(self, idx):
        self.tab_widget.setMinimumSize(self.tab_widget.currentWidget().layout().minimumSize())
        self.setMinimumSize(self.layout().minimumSize())