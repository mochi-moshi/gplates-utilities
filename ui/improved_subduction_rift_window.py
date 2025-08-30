"""
Improved Subduction/Rift Helper Window with intuitive workflow-based UI design.

This redesigned interface separates the three geological processes into distinct
workflows with guided steps and clear visual feedback.
"""

from os import path
from PySide6.QtWidgets import (
    QComboBox, QLabel, 
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
    QTabWidget, QGroupBox
)

from core.session import Session, FeatureDataColumn
from core.worldbuilding.diverge import diverge
from core.worldbuilding.rift import rift
from core.worldbuilding.subduct import subduct
from models.line_filter_model import LineFilterModel
from ui.components.process_step_widget import ProcessStepWidget
from ui.widgets.time_range_widget import TimeRangeWidget
from ui.widgets.feature_selector_widget import FeatureSelectorWidget
from ui.widgets.output_widget import OutputWidget
from ui.widgets.plate_id_widget import DualPlateIdWidget
from ui.base.process_tab_widget import ProcessTabWidget

from pygplates import FeatureCollection


class SubductionTabWidget(ProcessTabWidget):
    """Tab for subduction zone processing."""
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Workflow steps
        self.steps = [
            ProcessStepWidget(1, "Select Subduction Zone", 
                            "Choose the subduction zone that will consume features"),
            ProcessStepWidget(2, "Set Time Range", 
                            "Define when subduction occurs"),
            ProcessStepWidget(3, "Select Features to Subduct", 
                            "Choose features that will be processed by subduction"),
            ProcessStepWidget(4, "Process & Save", 
                            "Execute subduction and save results")
        ]
        
        for step in self.steps:
            layout.addWidget(step)
        
        # Step 1: Subduction zone selector
        self.sz_group = QGroupBox("Subduction Zone Selection")
        sz_layout = QVBoxLayout(self.sz_group)
        
        self.sz_model = LineFilterModel()
        self.sz_model.setFeatureTypeFilter(["SubductionZone"])
        self.sz_model.setSourceModel(self.session.get_feature_model())
        
        self.sz_selection = QComboBox()
        self.sz_selection.setModel(self.sz_model)
        self.sz_selection.setModelColumn(FeatureDataColumn.feature_name_and_id)
        self.sz_selection.setPlaceholderText("Select subduction zone...")
        self.sz_selection.currentIndexChanged.connect(lambda: self.update_step_status(0, True))
        
        sz_layout.addWidget(self.sz_selection)
        
        # Step 2: Time range
        self.time_group = QGroupBox("Time Range")
        self.time_widget = TimeRangeWidget()
        self.time_widget.timeChanged.connect(self.on_time_changed)
        
        time_layout = QVBoxLayout(self.time_group)
        time_layout.addWidget(self.time_widget)
        
        # Step 3: Feature selection
        self.feature_group = QGroupBox("Feature Selection")
        self.feature_selector = FeatureSelectorWidget(self.session)
        self.feature_selector.selectionChanged.connect(self.on_features_selected)
        
        feature_layout = QVBoxLayout(self.feature_group)
        feature_layout.addWidget(self.feature_selector)
        
        # Step 4: Output controls
        self.output_group = QGroupBox("Output")
        self.output_widget = OutputWidget(self.session)
        
        output_layout = QVBoxLayout(self.output_group)
        output_layout.addWidget(self.output_widget)
        
        # Process button
        self.process_button = QPushButton("🌋 Process Subduction")
        self.process_button.clicked.connect(self.process_subduction)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        output_layout.addWidget(self.process_button)
        
        layout.addWidget(self.sz_group)
        layout.addWidget(self.time_group)
        layout.addWidget(self.feature_group)
        layout.addWidget(self.output_group)
        
        # Set first step as active
        self.steps[0].set_active(True)
    
    def on_time_changed(self, start_time: float, end_time: float):
        """Handle time range changes."""
        self.feature_selector.set_time_filter(start_time, end_time)
        self.update_step_status(1, True)
        self.validate_and_enable_process()
        
    def on_features_selected(self, count: int):
        """Handle feature selection changes."""
        if count > 0:
            self.update_step_status(2, True)
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_sz = self.sz_selection.currentIndex() >= 0
        has_time = self.time_widget._validate_times()
        has_features = len(self.feature_selector.get_selected_features()) > 0
        has_output, _ = self.output_widget.is_valid()
        
        self.process_button.setEnabled(has_sz and has_time and has_features and has_output)
    
    def process_subduction(self):
        """Execute the subduction process."""
        try:
            # Get selected subduction zone
            sz_index = self.sz_selection.currentIndex()
            if sz_index < 0:
                QMessageBox.warning(self, "Error", "Please select a subduction zone")
                return
                
            sz_model_index = self.sz_model.index(sz_index, FeatureDataColumn.feature_id)
            sz_feature_id = self.sz_model.data(sz_model_index)
            sz_fc_name = self.sz_model.data(self.sz_model.index(sz_index, FeatureDataColumn.feature_collection_name))
            
            # Find the actual feature
            sz_fc = next(filter(lambda x: x.shortname == sz_fc_name, self.session.loaded_feature_collections)).feature_collection
            sz_feature = sz_fc.get(lambda f: f.get_feature_id().get_string() == sz_feature_id)
            
            if not sz_feature:
                QMessageBox.critical(self, "Error", "Could not find selected subduction zone")
                return
            
            # Get time range and features
            start_time, end_time = self.time_widget.get_times()
            selected_features = self.feature_selector.get_selected_features()
            
            if not self.session._rotationFeatureCollection:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Process subduction
            result_fc = subduct(
                selected_features,
                sz_feature,
                self.session._rotationFeatureCollection,
                start_time,
                end_time,
                use_topologies=self.output_widget.should_generate_topologies()
            )
            
            if len(result_fc) == 0:
                QMessageBox.information(self, "No Results", "Subduction processing returned no features")
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
                                  f"Subduction processing complete!\nResults saved to: {path.basename(output_path)}\n"
                                  f"Features processed: {len(selected_features)}\n"
                                  f"Features generated: {len(result_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Subduction processing failed:\n{str(e)}")


class RiftingTabWidget(ProcessTabWidget):
    """Tab for continental rifting processing."""
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Workflow steps
        self.steps = [
            ProcessStepWidget(1, "Select Rift", 
                            "Choose the continental rift feature"),
            ProcessStepWidget(2, "Set Split Time", 
                            "Define when rifting occurs (uses start time)"),
            ProcessStepWidget(3, "Select Features to Rift", 
                            "Choose features that will be split by rifting"),
            ProcessStepWidget(4, "Configure Rifting", 
                            "Set rifting parameters"),
            ProcessStepWidget(5, "Process & Save", 
                            "Execute rifting and save results")
        ]
        
        for step in self.steps:
            layout.addWidget(step)
        
        # Step 1: Rift selector
        self.rift_group = QGroupBox("Rift Selection")
        rift_layout = QVBoxLayout(self.rift_group)
        
        self.rift_model = LineFilterModel()
        self.rift_model.setFeatureTypeFilter(["ContinentalRift"])
        self.rift_model.setSourceModel(self.session.get_feature_model())
        
        self.rift_selection = QComboBox()
        self.rift_selection.setModel(self.rift_model)
        self.rift_selection.setModelColumn(FeatureDataColumn.feature_name_and_id)
        self.rift_selection.setPlaceholderText("Select rift...")
        self.rift_selection.currentIndexChanged.connect(lambda: self.update_step_status(0, True))
        
        rift_layout.addWidget(self.rift_selection)
        
        # Step 2: Time range (split time)
        self.time_group = QGroupBox("Split Time")
        self.time_widget = TimeRangeWidget()
        self.time_widget.timeChanged.connect(self.on_time_changed)
        
        time_layout = QVBoxLayout(self.time_group)
        time_layout.addWidget(self.time_widget)
        
        # Step 3: Feature selection
        self.feature_group = QGroupBox("Feature Selection")
        self.feature_selector = FeatureSelectorWidget(self.session)
        self.feature_selector.selectionChanged.connect(self.on_features_selected)
        
        feature_layout = QVBoxLayout(self.feature_group)
        feature_layout.addWidget(self.feature_selector)
        
        # Step 4: Rift parameters
        self.params_group = QGroupBox("Rifting Parameters")
        params_layout = QVBoxLayout(self.params_group)
        
        # Dual plate ID widget with validation
        self.plate_ids_widget = DualPlateIdWidget(self.session, enable_uniqueness_validation=True)
        self.plate_ids_widget.plateIdsChanged.connect(lambda left, right: self.update_step_status(3, True))
        
        params_layout.addWidget(self.plate_ids_widget)
        
        # Step 5: Output controls
        self.output_group = QGroupBox("Output")
        self.output_widget = OutputWidget(self.session)
        
        output_layout = QVBoxLayout(self.output_group)
        output_layout.addWidget(self.output_widget)
        
        # Process button
        self.process_button = QPushButton("🏔️ Process Rifting")
        self.process_button.clicked.connect(self.process_rifting)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #8BC34A;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7CB342;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        output_layout.addWidget(self.process_button)
        
        layout.addWidget(self.rift_group)
        layout.addWidget(self.time_group)
        layout.addWidget(self.feature_group)
        layout.addWidget(self.params_group)
        layout.addWidget(self.output_group)
        
        # Set first step as active
        self.steps[0].set_active(True)
    
    def on_time_changed(self, start_time: float, end_time: float):
        """Handle time range changes."""
        self.feature_selector.set_time_filter(start_time, end_time)
        self.update_step_status(1, True)
        self.validate_and_enable_process()
        
    def on_features_selected(self, count: int):
        """Handle feature selection changes."""
        if count > 0:
            self.update_step_status(2, True)
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_rift = self.rift_selection.currentIndex() >= 0
        has_time = self.time_widget._validate_times()
        has_features = len(self.feature_selector.get_selected_features()) > 0
        has_output, _ = self.output_widget.is_valid()
        
        self.process_button.setEnabled(has_rift and has_time and has_features and has_output)
    
    def process_rifting(self):
        """Execute the rifting process."""
        try:
            # Get selected rift
            rift_index = self.rift_selection.currentIndex()
            if rift_index < 0:
                QMessageBox.warning(self, "Error", "Please select a rift")
                return
                
            rift_model_index = self.rift_model.index(rift_index, FeatureDataColumn.feature_id)
            rift_feature_id = self.rift_model.data(rift_model_index)
            rift_fc_name = self.rift_model.data(self.rift_model.index(rift_index, FeatureDataColumn.feature_collection_name))
            
            # Find the actual feature
            rift_fc = next(filter(lambda x: x.shortname == rift_fc_name, self.session.loaded_feature_collections)).feature_collection
            rift_feature = rift_fc.get(lambda f: f.get_feature_id().get_string() == rift_feature_id)
            
            if not rift_feature:
                QMessageBox.critical(self, "Error", "Could not find selected rift")
                return
            
            # Get parameters
            start_time, end_time = self.time_widget.get_times()
            selected_features = self.feature_selector.get_selected_features()
            
            # Get validated plate IDs
            try:
                left_plate_id, right_plate_id = self.plate_ids_widget.get_plate_ids()
            except ValueError as e:
                QMessageBox.warning(self, "Invalid Plate IDs", str(e))
                return
            
            # Use start_time as the split_time for rifting
            split_time = start_time
            
            if not self.session._rotationFeatureCollection:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Process rifting
            result_fc = rift(
                selected_features,
                rift_feature,
                self.session._rotationModel,
                split_time,
                left_plate_id,
                right_plate_id,
                use_topologies=self.output_widget.should_generate_topologies()
            )
            
            if len(result_fc) == 0:
                QMessageBox.information(self, "No Results", "Rifting processing returned no features")
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
                                  f"Rifting processing complete!\nResults saved to: {path.basename(output_path)}\n"
                                  f"Features processed: {len(selected_features)}\n"
                                  f"Features generated: {len(result_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Rifting processing failed:\n{str(e)}")


class DivergenceTabWidget(ProcessTabWidget):
    """Tab for ocean spreading/divergence processing."""
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Workflow steps
        self.steps = [
            ProcessStepWidget(1, "Select Ridge", 
                            "Choose the mid-ocean ridge for spreading"),
            ProcessStepWidget(2, "Set Time Range", 
                            "Define when ocean spreading occurs"),
            ProcessStepWidget(3, "Process & Save", 
                            "Execute spreading and save results")
        ]
        
        for step in self.steps:
            layout.addWidget(step)
        
        # Step 1: Ridge selector
        self.ridge_group = QGroupBox("Ridge Selection")
        ridge_layout = QVBoxLayout(self.ridge_group)
        
        self.ridge_model = LineFilterModel()
        self.ridge_model.setFeatureTypeFilter(["MidOceanRidge"])
        self.ridge_model.setSourceModel(self.session.get_feature_model())
        
        self.ridge_selection = QComboBox()
        self.ridge_selection.setModel(self.ridge_model)
        self.ridge_selection.setModelColumn(FeatureDataColumn.feature_name_and_id)
        self.ridge_selection.setPlaceholderText("Select mid-ocean ridge...")
        self.ridge_selection.currentIndexChanged.connect(lambda: self.update_step_status(0, True))
        
        ridge_layout.addWidget(self.ridge_selection)
        
        # Step 2: Time range
        self.time_group = QGroupBox("Time Range")
        self.time_widget = TimeRangeWidget()
        self.time_widget.timeChanged.connect(self.on_time_changed)
        
        time_layout = QVBoxLayout(self.time_group)
        time_layout.addWidget(self.time_widget)
        
        # Step 3: Output controls
        self.output_group = QGroupBox("Output")
        self.output_widget = OutputWidget(self.session)
        
        output_layout = QVBoxLayout(self.output_group)
        output_layout.addWidget(self.output_widget)
        
        # Process button
        self.process_button = QPushButton("🌊 Process Ocean Spreading")
        self.process_button.clicked.connect(self.process_divergence)
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
        
        layout.addWidget(self.ridge_group)
        layout.addWidget(self.time_group)
        layout.addWidget(self.output_group)
        
        # Set first step as active
        self.steps[0].set_active(True)
    
    def on_time_changed(self, start_time: float, end_time: float):
        """Handle time range changes."""
        self.update_step_status(1, True)
        self.validate_and_enable_process()
    
    def validate_and_enable_process(self):
        """Validate inputs and enable process button if ready."""
        has_ridge = self.ridge_selection.currentIndex() >= 0
        has_time = self.time_widget._validate_times()
        has_output, _ = self.output_widget.is_valid()
        
        self.process_button.setEnabled(has_ridge and has_time and has_output)
    
    def process_divergence(self):
        """Execute the ocean spreading process."""
        try:
            # Get selected ridge
            ridge_index = self.ridge_selection.currentIndex()
            if ridge_index < 0:
                QMessageBox.warning(self, "Error", "Please select a mid-ocean ridge")
                return
                
            ridge_model_index = self.ridge_model.index(ridge_index, FeatureDataColumn.feature_id)
            ridge_feature_id = self.ridge_model.data(ridge_model_index)
            ridge_fc_name = self.ridge_model.data(self.ridge_model.index(ridge_index, FeatureDataColumn.feature_collection_name))
            
            # Find the actual feature
            ridge_fc = next(filter(lambda x: x.shortname == ridge_fc_name, self.session.loaded_feature_collections)).feature_collection
            ridge_feature = ridge_fc.get(lambda f: f.get_feature_id().get_string() == ridge_feature_id)
            
            if not ridge_feature:
                QMessageBox.critical(self, "Error", "Could not find selected ridge")
                return
            
            # Get parameters
            start_time, end_time = self.time_widget.get_times()
            
            if not self.session._rotationFeatureCollection:
                QMessageBox.critical(self, "Error", "No rotation model loaded")
                return
            
            # Process divergence
            result_fc = diverge(
                ridge_feature,
                self.session._rotationFeatureCollection,
                start_time,
                end_time,
                use_topologies=self.output_widget.should_generate_topologies()
            )
            
            if len(result_fc) == 0:
                QMessageBox.information(self, "No Results", "Ocean spreading processing returned no features")
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
            
            self.update_step_status(2, True)
            QMessageBox.information(self, "Success", 
                                  f"Ocean spreading processing complete!\nResults saved to: {path.basename(output_path)}\n"
                                  f"Features generated: {len(result_fc)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocean spreading processing failed:\n{str(e)}")


class ImprovedSubductionRiftHelperWindow(QWidget):
    """
    Improved Subduction/Rift Helper Window with guided workflows.
    
    Features:
    - Separate tabs for subduction, rifting, and ocean spreading
    - Step-by-step visual workflows
    - Integrated validation and error handling
    - Advanced output options
    """
    
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        
        self.setWindowTitle("Geological Process Helper")
        self.setMinimumSize(1000, 700)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main UI components."""
        layout = QVBoxLayout(self)
        
        # Header info
        header_label = QLabel("""
        <h2>🌋 Geological Process Helper</h2>
        <p>This tool provides guided workflows for modeling geological processes through time.
        Each process is separated into clear steps with validation and visual feedback.</p>
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
        
        # Tab widget for different processes
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Create tabs
        self.subduction_tab = SubductionTabWidget(self.session)
        self.rifting_tab = RiftingTabWidget(self.session)
        self.divergence_tab = DivergenceTabWidget(self.session)
        
        # Add tabs with emojis for visual appeal
        self.tab_widget.addTab(self.subduction_tab, "🌋 Subduction")
        self.tab_widget.addTab(self.rifting_tab, "🏔️ Rifting")  
        self.tab_widget.addTab(self.divergence_tab, "🌊 Ocean Spreading")
        
        # Set tab tooltips
        self.tab_widget.setTabToolTip(0, "Process feature consumption through subduction zones")
        self.tab_widget.setTabToolTip(1, "Model continental rifting and plate splitting")
        self.tab_widget.setTabToolTip(2, "Generate ocean crust from mid-ocean ridges")
        
        layout.addWidget(self.tab_widget)