"""
Improved Plate Operations Window with intuitive workflow-based UI design.

This redesigned interface combines plate splitting, polygon operations, and line splitting
functionality into a unified, guided workflow with clear visual feedback.
"""

from os import path
from PySide6.QtCore import Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, 
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
    QTabWidget, QGroupBox, QCheckBox, QSpinBox,
    QFormLayout
)

from core.session import Session, FeatureDataColumn
from core.plate_splitter import split_plate_features
from core.line_splitter import split_line_features
from core.polygon_operations import join_plate_features_by_intersect, join_plate_features_by_union, split_plate_features_by_difference
from models.line_filter_model import LineFilterModel
from models.polygon_filter_model import PolygonFilterModel
from ui.components.process_step_widget import ProcessStepWidget
from ui.widgets.time_range_widget import TimeRangeWidget
from ui.widgets.feature_selector_widget import FeatureSelectorWidget
from ui.widgets.output_widget import OutputWidget
from ui.widgets.plate_id_widget import PlateIdWidget
from ui.base.process_tab_widget import ProcessTabWidget

from pygplates import FeatureCollection


class PlateSplittingTabWidget(ProcessTabWidget):
    """Tab for splitting plates using geological features."""
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Workflow steps
        self.steps = [
            ProcessStepWidget(1, "Select Splitting Feature", 
                            "Choose the geological feature that will split the plates"),
            ProcessStepWidget(2, "Set Split Time", 
                            "Define when plate splitting occur"),
            ProcessStepWidget(3, "Select Plates to Split", 
                            "Choose which plates will be affected by splitting"),
            ProcessStepWidget(4, "Process & Save", 
                            "Execute splitting and save results")
        ]
        
        for step in self.steps:
            layout.addWidget(step)
        
        # Step 1: Splitting feature selector
        self.splitter_group = QGroupBox("Splitting Feature Selection")
        splitter_layout = QVBoxLayout(self.splitter_group)
        
        self.splitter_model = LineFilterModel()
        self.splitter_model.setSourceModel(self.session.get_feature_model())
        
        self.splitter_selection = QComboBox()
        self.splitter_selection.setModel(self.splitter_model)
        self.splitter_selection.setModelColumn(FeatureDataColumn.feature_name_and_id)
        self.splitter_selection.setPlaceholderText("Select splitting feature...")
        self.splitter_selection.currentIndexChanged.connect(lambda: self.update_step_status(0, True))
        
        splitter_layout.addWidget(self.splitter_selection)
        
        # Step 2: Split time
        self.time_group = QGroupBox("Split Time")
        time_layout = QFormLayout(self.time_group)
        
        self.split_time = QLineEdit()
        self.split_time.setValidator(QDoubleValidator())
        self.split_time.setPlaceholderText("e.g., 10.0")
        self.split_time.textChanged.connect(lambda: self.on_time_changed())
        
        time_layout.addRow("Split Time (Ma):", self.split_time)
        
        # Step 3: Feature selection
        self.feature_group = QGroupBox("Plate Selection")
        self.feature_selector = FeatureSelectorWidget(self.session)
        self.feature_selector.selectionChanged.connect(self.on_features_selected)
        
        feature_layout = QVBoxLayout(self.feature_group)
        feature_layout.addWidget(self.feature_selector)
        
        # Step 5: Output controls
        self.output_group = QGroupBox("Output")
        self.output_widget = OutputWidget(self.session, enable_topology_generation=False)
        self.output_widget.pathChange.connect(lambda: self.validate_and_enable_process())
        
        output_layout = QVBoxLayout(self.output_group)
        output_layout.addWidget(self.output_widget)
        
        # Process button
        self.process_button = QPushButton("🔪 Split Plates")
        self.process_button.clicked.connect(self.process_splitting)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
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
        output_layout.addWidget(self.process_button)
        
        layout.addWidget(self.splitter_group)
        layout.addWidget(self.time_group)
        layout.addWidget(self.feature_group)
        layout.addWidget(self.output_group)
        
        # Set first step as active
        self.steps[0].set_active(True)

    def on_time_changed(self):
        """Handle time changes."""
        self.splitter_model.setTimeFilter(float(self.split_time.text()) if self.split_time.text() else None)
        self.update_step_status(1, bool(self.split_time.text()))
        self.validate_and_enable_process()
    
    def on_features_selected(self, count: int):
        """Handle feature selection changes."""
        if count > 0:
            self.update_step_status(2, True)
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_splitter = self.splitter_selection.currentIndex() >= 0
        has_time = bool(self.split_time.text())
        has_features = len(self.feature_selector.get_selected_features()) > 0
        has_output, _ = self.output_widget.is_valid()
        
        self.process_button.setEnabled(has_splitter and has_time and has_features and has_output)
    
    def process_splitting(self):
        """Execute the plate splitting process."""
        try:
            # Get selected splitter
            splitter_index = self.splitter_selection.currentIndex()
            if splitter_index < 0:
                QMessageBox.warning(self, "Error", "Please select a splitting feature")
                return
                
            splitter_model_index = self.splitter_model.index(splitter_index, FeatureDataColumn.feature_id)
            splitter_feature_id = self.splitter_model.data(splitter_model_index)
            splitter_fc_name = self.splitter_model.data(self.splitter_model.index(splitter_index, FeatureDataColumn.feature_collection))
            
            # Find the actual feature
            splitter_fc = next(filter(lambda x: x.shortname == splitter_fc_name, self.session.loaded_feature_collections)).feature_collection
            splitter_feature = splitter_fc.get(lambda f: f.get_feature_id().get_string() == splitter_feature_id)
            
            if not splitter_feature:
                QMessageBox.critical(self, "Error", "Could not find selected splitting feature")
                return
            
            # Get parameters
            split_time = float(self.split_time.text())
            selected_features = self.feature_selector.get_selected_features()
            
            if not self.session._rotationModel:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Process splitting
            result_fc = split_plate_features(
                selected_features,
                splitter_feature,
                self.session._rotationModel,
                split_time
            )
            
            if len(result_fc) == 0:
                QMessageBox.information(self, "No Results", "Plate splitting returned no features")
                return
            
            # Save results
            output_path = self.output_widget.get_output_path()
            
            if self.output_widget.should_append() and path.exists(output_path):
                existing_fc = FeatureCollection(output_path)
                for feature in result_fc:
                    existing_fc.add(feature)
                existing_fc.write(output_path)
            else:
                result_fc.write(output_path)
            
            self.update_step_status(3, True)
            QMessageBox.information(self, "Success", 
                                  f"Plate splitting complete!\nResults saved to: {path.basename(output_path)}\n"
                                  f"Features processed: {len(selected_features)}\n"
                                  f"Features generated: {len(result_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Plate splitting failed:\n{str(e)}")
            

class LineSplittingTabWidget(ProcessTabWidget):
    """Tab for splitting line features at their intersections."""
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Workflow steps  
        self.steps = [
            ProcessStepWidget(1, "Select First Line", 
                            "Choose the first line feature to split"),
            ProcessStepWidget(2, "Select Second Line", 
                            "Choose the second line feature to split"),
            ProcessStepWidget(3, "Set Split Time", 
                            "Define when line splitting occurs"),
            ProcessStepWidget(4, "Process & Save", 
                            "Split lines at intersections and save results")
        ]
        
        for step in self.steps:
            layout.addWidget(step)
        
        # Step 1: First line selection
        self.line1_group = QGroupBox("First Line Selection")
        line1_layout = QVBoxLayout(self.line1_group)
        
        self.line1_model = LineFilterModel()
        self.line1_model.setSourceModel(self.session.get_feature_model())
        
        self.line1_selection = QComboBox()
        self.line1_selection.setModel(self.line1_model)
        self.line1_selection.setModelColumn(FeatureDataColumn.feature_name_and_id)
        self.line1_selection.setPlaceholderText("Select first line...")
        self.line1_selection.currentIndexChanged.connect(lambda: self.update_step_status(0, True))
        
        line1_layout.addWidget(self.line1_selection)
        
        # Step 2: Second line selection
        self.line2_group = QGroupBox("Second Line Selection")
        line2_layout = QVBoxLayout(self.line2_group)
        
        self.line2_model = LineFilterModel()
        self.line2_model.setSourceModel(self.session.get_feature_model())
        
        self.line2_selection = QComboBox()
        self.line2_selection.setModel(self.line2_model)
        self.line2_selection.setModelColumn(FeatureDataColumn.feature_name_and_id)
        self.line2_selection.setPlaceholderText("Select second line...")
        self.line2_selection.currentIndexChanged.connect(lambda: self.update_step_status(1, True))
        
        line2_layout.addWidget(self.line2_selection)
        
        # Step 3: Split time
        self.time_group = QGroupBox("Split Time")
        time_layout = QFormLayout(self.time_group)
        
        self.split_time = QLineEdit()
        self.split_time.setValidator(QDoubleValidator())
        self.split_time.setPlaceholderText("e.g., 10.0")
        self.split_time.textChanged.connect(lambda: self.update_step_status(2, bool(self.split_time.text())))
        
        time_layout.addRow("Split Time (Ma):", self.split_time)
        
        # Step 4: Output controls
        self.output_group = QGroupBox("Output")
        self.output_widget = OutputWidget(self.session, enable_topology_generation=False)
        self.output_widget.pathChange.connect(lambda: self.validate_and_enable_process())
        
        output_layout = QVBoxLayout(self.output_group)
        output_layout.addWidget(self.output_widget)
        
        # Process button
        self.process_button = QPushButton("✂️ Split Lines")
        self.process_button.clicked.connect(self.process_line_splitting)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8E24AA;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        output_layout.addWidget(self.process_button)
        
        layout.addWidget(self.line1_group)
        layout.addWidget(self.line2_group)
        layout.addWidget(self.time_group)
        layout.addWidget(self.output_group)
        
        # Set first step as active
        self.steps[0].set_active(True)
    
    def on_time_changed(self, start_time: float, end_time: float):
        """Handle time range changes."""
        self.line_selector.set_time_filter(start_time, end_time)
        self.update_step_status(1, True)
        self.validate_and_enable_process()
        
    def on_lines_selected(self, count: int):
        """Handle line selection changes."""
        if count >= 2:  # Need at least 2 lines for intersections
            self.update_step_status(0, True)
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_line1 = self.line1_selection.currentIndex() >= 0
        has_line2 = self.line2_selection.currentIndex() >= 0
        has_time = bool(self.split_time.text())
        has_output, _ = self.output_widget.is_valid()
        
        self.process_button.setEnabled(has_line1 and has_line2 and has_time and has_output)
    
    def process_line_splitting(self):
        """Execute the line splitting process."""
        try:
            # Get selected lines
            line1_index = self.line1_selection.currentIndex()
            line2_index = self.line2_selection.currentIndex()
            
            if line1_index < 0:
                QMessageBox.warning(self, "Error", "Please select first line")
                return
            if line2_index < 0:
                QMessageBox.warning(self, "Error", "Please select second line")
                return
                
            # Get the actual features
            line1_model_index = self.line1_model.index(line1_index, FeatureDataColumn.feature_id)
            line1_feature_id = self.line1_model.data(line1_model_index)
            line1_fc_name = self.line1_model.data(self.line1_model.index(line1_index, FeatureDataColumn.feature_collection))
            
            line1_fc = next(filter(lambda x: x.shortname == line1_fc_name, self.session.loaded_feature_collections)).feature_collection
            line1_feature = line1_fc.get(lambda f: f.get_feature_id().get_string() == line1_feature_id)
            
            line2_model_index = self.line2_model.index(line2_index, FeatureDataColumn.feature_id)
            line2_feature_id = self.line2_model.data(line2_model_index)
            line2_fc_name = self.line2_model.data(self.line2_model.index(line2_index, FeatureDataColumn.feature_collection))
            
            line2_fc = next(filter(lambda x: x.shortname == line2_fc_name, self.session.loaded_feature_collections)).feature_collection
            line2_feature = line2_fc.get(lambda f: f.get_feature_id().get_string() == line2_feature_id)
            
            if not line1_feature:
                QMessageBox.critical(self, "Error", "Could not find selected first line")
                return
            if not line2_feature:
                QMessageBox.critical(self, "Error", "Could not find selected second line")
                return
            
            # Get parameters
            split_time = float(self.split_time.text())
                
            if not self.session._rotationModel:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Process line splitting
            result_fc = split_line_features(
                line1_feature,
                line2_feature,
                self.session._rotationModel,
                split_time
            )
            
            if len(result_fc) == 0:
                QMessageBox.information(self, "No Results", "No line intersections found")
                return
            
            # Save results
            output_path = self.output_widget.get_output_path()
            
            if self.output_widget.should_append() and path.exists(output_path):
                existing_fc = FeatureCollection(output_path)
                for feature in result_fc:
                    existing_fc.add(feature)
                existing_fc.write(output_path)
            else:
                result_fc.write(output_path)
            
            self.update_step_status(3, True)
            QMessageBox.information(self, "Success", 
                                  f"Line splitting complete!\nResults saved to: {path.basename(output_path)}\n"
                                  f"Split segments generated: {len(result_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Line splitting failed:\n{str(e)}")


class PolygonOperationsTabWidget(ProcessTabWidget):
    """Tab for geometric polygon operations (intersection, union, difference)."""
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Workflow steps
        self.steps = [
            ProcessStepWidget(1, "Select Polygon Features", 
                            "Choose polygon features for geometric operation"),
            ProcessStepWidget(2, "Set Split Time", 
                            "Define the split time for operation"),
            ProcessStepWidget(3, "Choose Operation Type", 
                            "Select intersection, union, or difference operation"),
            ProcessStepWidget(4, "Configure Parameters", 
                            "Set operation parameters and output options"),
            ProcessStepWidget(5, "Process & Save", 
                            "Execute operation and save results")
        ]
        
        for step in self.steps:
            layout.addWidget(step)
        
        # Step 1: Polygon selection
        self.polygon_group = QGroupBox("Polygon Feature Selection")
        polygon_layout = QVBoxLayout(self.polygon_group)
        
        self.polygon_model = PolygonFilterModel()
        self.polygon_model.setSourceModel(self.session.get_feature_model())
        
        self.polygon_selector = FeatureSelectorWidget(self.session)
        self.polygon_selector.selectionChanged.connect(self.on_polygons_selected)
        
        polygon_layout.addWidget(self.polygon_selector)
        
        # Step 2: Split time
        self.time_group = QGroupBox("Split Time")
        time_layout = QFormLayout(self.time_group)
        
        self.split_time = QLineEdit()
        self.split_time.setValidator(QDoubleValidator())
        self.split_time.setPlaceholderText("e.g., 10.0")
        self.split_time.textChanged.connect(lambda: self.update_step_status(1, bool(self.split_time.text())))
        
        time_layout.addRow("Split Time (Ma):", self.split_time)
        
        # Step 3: Operation selection
        self.operation_group = QGroupBox("Operation Type")
        operation_layout = QVBoxLayout(self.operation_group)
        
        # Operation buttons with different colors
        self.intersection_button = QPushButton("∩ Intersection")
        self.intersection_button.setCheckable(True)
        self.intersection_button.clicked.connect(lambda: self.select_operation("intersection"))
        self.intersection_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:checked {
                background-color: #2E7D32;
            }
        """)
        
        self.union_button = QPushButton("∪ Union")
        self.union_button.setCheckable(True)
        self.union_button.clicked.connect(lambda: self.select_operation("union"))
        self.union_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:checked {
                background-color: #1565C0;
            }
        """)
        
        self.difference_button = QPushButton("− Difference")
        self.difference_button.setCheckable(True)
        self.difference_button.clicked.connect(lambda: self.select_operation("difference"))
        self.difference_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:checked {
                background-color: #D84315;
            }
        """)
        
        operation_layout.addWidget(self.intersection_button)
        operation_layout.addWidget(self.union_button)
        operation_layout.addWidget(self.difference_button)
        
        # Step 4: Parameters
        self.params_group = QGroupBox("Operation Parameters")
        params_layout = QVBoxLayout(self.params_group)
        
        # Plate ID widget with validation
        self.plate_id_widget = PlateIdWidget(self.session, "New Plate ID", enable_uniqueness_validation=True)
        
        self.duplicate_per_plate = QCheckBox("Create separate result per plate")
        
        params_layout.addWidget(self.plate_id_widget)
        params_layout.addWidget(self.duplicate_per_plate)
        
        # Step 5: Output controls
        self.output_group = QGroupBox("Output")
        self.output_widget = OutputWidget(self.session, enable_topology_generation=False)
        self.output_widget.pathChange.connect(lambda: self.validate_and_enable_process())
        
        output_layout = QVBoxLayout(self.output_group)
        output_layout.addWidget(self.output_widget)
        
        # Process button
        self.process_button = QPushButton("⚙️ Process Operation")
        self.process_button.clicked.connect(self.process_operation)
        self.process_button.setEnabled(False)
        
        output_layout.addWidget(self.process_button)
        
        layout.addWidget(self.polygon_group)
        layout.addWidget(self.time_group)
        layout.addWidget(self.operation_group)
        layout.addWidget(self.params_group)
        layout.addWidget(self.output_group)
        
        # Set first step as active
        self.steps[0].set_active(True)
        self.selected_operation = None
    
    def select_operation(self, operation: str):
        """Select operation type and update UI."""
        # Clear other selections
        self.intersection_button.setChecked(operation == "intersection")
        self.union_button.setChecked(operation == "union")
        self.difference_button.setChecked(operation == "difference")
        
        self.selected_operation = operation
        self.update_step_status(2, True)
        
        # Update process button style based on operation
        colors = {
            "intersection": "#4CAF50",
            "union": "#2196F3", 
            "difference": "#FF5722"
        }
        
        self.process_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors[operation]};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:disabled {{
                background-color: #ccc;
                color: #999;
            }}
        """)
        
        self.validate_and_enable_process()
    
    def on_polygons_selected(self, count: int):
        """Handle polygon selection changes."""
        if count >= 2:  # Need at least 2 polygons for operations
            self.update_step_status(0, True)
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_polygons = len(self.polygon_selector.get_selected_features()) >= 2
        has_time = bool(self.split_time.text())
        has_operation = self.selected_operation is not None
        has_output, _ = self.output_widget.is_valid()
        
        if has_polygons and has_time and has_operation:
            self.update_step_status(3, True)
        
        self.process_button.setEnabled(has_polygons and has_time and has_operation and has_output)
    
    def process_operation(self):
        """Execute the polygon operation."""
        try:
            if not self.selected_operation:
                QMessageBox.warning(self, "Error", "Please select an operation type")
                return
            
            # Get parameters
            split_time = float(self.split_time.text())
            selected_features = self.polygon_selector.get_selected_features()
            
            # Get validated plate ID (only if not duplicating per plate)
            if not self.duplicate_per_plate.isChecked():
                try:
                    new_plate_id = self.plate_id_widget.get_plate_id()
                except ValueError as e:
                    QMessageBox.warning(self, "Invalid Plate ID", str(e))
                    return
            else:
                new_plate_id = None  # Will be handled by the operation function
            
            if len(selected_features) < 2:
                QMessageBox.warning(self, "Error", "Please select at least 2 polygon features")
                return
                
            if not self.session._rotationModel:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Choose operation function
            operation_funcs = {
                "intersection": join_plate_features_by_intersect,
                "union": join_plate_features_by_union,
                "difference": split_plate_features_by_difference
            }
            
            operation_func = operation_funcs[self.selected_operation]
            
            # Process operation
            result_fc = operation_func(
                selected_features,
                self.session._rotationModel,
                split_time,
                reconstruction_plate_id=new_plate_id
            )
            
            if len(result_fc) == 0:
                QMessageBox.information(self, "No Results", f"{self.selected_operation.title()} operation returned no features")
                return
            
            # Save results
            output_path = self.output_widget.get_output_path()
            
            if self.output_widget.should_append() and path.exists(output_path):
                existing_fc = FeatureCollection(output_path)
                for feature in result_fc:
                    existing_fc.add(feature)
                existing_fc.write(output_path)
            else:
                result_fc.write(output_path)
            
            self.update_step_status(4, True)
            QMessageBox.information(self, "Success", 
                                  f"Polygon {self.selected_operation} complete!\nResults saved to: {path.basename(output_path)}\n"
                                  f"Features processed: {len(selected_features)}\n"
                                  f"Features generated: {len(result_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Polygon operation failed:\n{str(e)}")


class ImprovedPlateOperationsWindow(QWidget):
    """
    Improved Plate Operations Window with guided workflows.
    
    Features:
    - Separate tabs for plate splitting, line operations, and polygon operations
    - Step-by-step visual workflows
    - Integrated validation and error handling
    - Advanced output options
    """
    
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        
        self.setWindowTitle("Plate Operations Helper")
        self.setMinimumSize(1000, 700)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main UI components."""
        layout = QVBoxLayout(self)
        
        # Header info
        header_label = QLabel("""
        <h2>🌍 Plate Operations Helper</h2>
        <p>This tool provides guided workflows for various plate tectonic operations.
        Each operation is separated into clear steps with validation and visual feedback.</p>
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
        self.plate_splitting_tab = PlateSplittingTabWidget(self.session)
        self.line_splitting_tab = LineSplittingTabWidget(self.session)
        self.polygon_operations_tab = PolygonOperationsTabWidget(self.session)
        
        # Add tabs with emojis for visual appeal
        self.tab_widget.addTab(self.plate_splitting_tab, "🔪 Plate Splitting")
        self.tab_widget.addTab(self.line_splitting_tab, "✂️ Line Splitting")
        self.tab_widget.addTab(self.polygon_operations_tab, "⚙️ Polygon Operations")
        
        # Set tab tooltips
        self.tab_widget.setTabToolTip(0, "Split plates using geological features")
        self.tab_widget.setTabToolTip(1, "Find and create features at line intersections")
        self.tab_widget.setTabToolTip(2, "Perform geometric operations on polygon features")
        
        layout.addWidget(self.tab_widget)