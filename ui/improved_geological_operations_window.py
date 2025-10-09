"""
Improved Geological Operations Window - Master Interface

This comprehensive interface combines all geological operations into a unified,
tabbed window with consistent workflows and visual design patterns.
"""

from os import path
from PyQt5.QtCore import QTimer, pyqtSlot, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget,
    QTabWidget, QGridLayout, QMainWindow, QFrame
)

from core.session import Session
from ui.feature_collection_loader import FeatureCollectionLoader
from ui.improved_subduction_rift_window import ImprovedSubductionRiftHelperWindow
from ui.improved_plate_operations_window import ImprovedPlateOperationsWindow
from ui.improved_rotation_management_window import ImprovedRotationManagementWindow
from ui.components.operation_summary_widget import OperationSummaryWidget
from ui.components.welcome_tab_widget import WelcomeTabWidget
from util.project_storage import load_project, save_project
from media import LOGO_PATH


class ImprovedGeologicalOperationsWindow(QMainWindow):
    """
    Master geological operations window combining all geological modeling functionality.
    
    Features:
    - Welcome tab with operation overview
    - Geological processes (subduction, rifting, spreading)
    - Plate operations (splitting, intersections, unions)
    - Rotation management (initialization, creation, maintenance)
    - Consistent UI/UX across all operations
    - Integrated help and documentation
    - Session state management
    """
    
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        
        self.setWindowTitle("GPlates Operations Suite")
        # self.setMinimumSize(1200, 800)
        # self.resize(1200, 800)

        self.feature_collection_manager = FeatureCollectionLoader(self.session)
        
        # Set application icon (if available)
        self.setWindowIcon(QIcon(LOGO_PATH))
      
        self.setup_menu_bar()
        self.setup_ui()
        self.setup_status_bar()
        
    def setup_ui(self):
        """Setup the main UI components."""
        # Central widget and main tab widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Main tab widget
        self.main_tab_widget = QTabWidget()
        self.main_tab_widget.setTabPosition(QTabWidget.North)
        self.main_tab_widget.setMovable(True)
        self.main_tab_widget.setTabsClosable(False)
        
        # Create operation windows
        self.welcome_tab = WelcomeTabWidget()
        self.geological_window = ImprovedSubductionRiftHelperWindow(self.session)
        self.plate_operations_window = ImprovedPlateOperationsWindow(self.session)
        self.rotation_management_window = ImprovedRotationManagementWindow(self.session)
        
        # Add tabs with icons
        self.main_tab_widget.addTab(self.welcome_tab, "🏠 Welcome")
        self.main_tab_widget.addTab(self.geological_window, "🌋 Geological Processes")
        self.main_tab_widget.addTab(self.plate_operations_window, "🌍 Plate Operations")
        self.main_tab_widget.addTab(self.rotation_management_window, "🔄 Rotation Management")
        
        # Set tab tooltips
        self.main_tab_widget.setTabToolTip(0, "Overview and quick access to all operations")
        self.main_tab_widget.setTabToolTip(1, "Subduction, rifting, and ocean spreading operations")
        self.main_tab_widget.setTabToolTip(2, "Plate splitting and geometric operations")
        self.main_tab_widget.setTabToolTip(3, "Rotation model creation and management")
        
        layout.addWidget(self.main_tab_widget)
        
        # Connect welcome tab signals
        self.welcome_tab.operationSelected.connect(self.navigate_to_operation)
        
    def setup_menu_bar(self):
        """Setup menu bar similar to the original MainWindow."""
        # File Menu
        file_menu = self.menuBar().addMenu("File")
        
        new_project_action = file_menu.addAction("New Project")
        new_project_action.triggered.connect(self.new_project)
        load_project_action = file_menu.addAction("Open Project")
        load_project_action.triggered.connect(self.open_project)
        save_project_action = file_menu.addAction("Save Project")
        save_project_action.triggered.connect(self.save_project)
        
        file_menu.addSeparator()
        
        manage_feature_collection_action = file_menu.addAction("Manage Feature Collections")
        manage_feature_collection_action.triggered.connect(self.feature_collection_manager.show)
        load_feature_collection_action = file_menu.addAction("Open Feature Collection(s)")
        load_feature_collection_action.triggered.connect(self.open_feature_collections)
        load_rotation_model_action = file_menu.addAction("Open Rotation Model")
        load_rotation_model_action.triggered.connect(self.open_rotation_model)
        
        file_menu.addSeparator()
        
        reload_action = file_menu.addAction("Reload Files")
        reload_action.triggered.connect(self.reload_files)
        
        # View Menu
        view_menu = self.menuBar().addMenu("View")
        
        welcome_action = view_menu.addAction("Welcome")
        welcome_action.triggered.connect(lambda: self.main_tab_widget.setCurrentIndex(0))
        geological_action = view_menu.addAction("Geological Processes")
        geological_action.triggered.connect(lambda: self.main_tab_widget.setCurrentIndex(1))
        plate_action = view_menu.addAction("Plate Operations")
        plate_action.triggered.connect(lambda: self.main_tab_widget.setCurrentIndex(2))
        rotation_action = view_menu.addAction("Rotation Management")
        rotation_action.triggered.connect(lambda: self.main_tab_widget.setCurrentIndex(3))
        
        # Help Menu
        help_menu = self.menuBar().addMenu("Help")
        
        help_action = help_menu.addAction("Help Documentation")
        help_action.triggered.connect(self.show_help)
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
      
    def setup_status_bar(self):
        """Setup status bar for information display."""
        # Use QMainWindow's built-in status bar
        status_bar = self.statusBar()
        status_bar.showMessage("Ready - Select an operation to begin")
        
        # Update status based on session state
        self.update_status()
        
        # Update status periodically
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Update every 5 seconds
    
    def navigate_to_operation(self, operation_category: str):
        """Navigate to the specified operation category."""
        tab_map = {
            "Geological Processes": 1,
            "Plate Operations": 2, 
            "Rotation Management": 3
        }
        
        if operation_category in tab_map:
            self.main_tab_widget.setCurrentIndex(tab_map[operation_category])
            self.statusBar().showMessage(f"Navigated to {operation_category}")
    
    def update_status(self):
        """Update the status bar with current session information."""
        try:
            # Count loaded features
            feature_count = sum(len(lfc.feature_collection) for lfc in self.session.loaded_feature_collections)
            
            # Check rotation model
            has_rotation = "✓" if self.session._rotationModel else "✗"
            
            # Current tab
            current_tab = self.main_tab_widget.tabText(self.main_tab_widget.currentIndex())
            
            status = f"Features: {feature_count} | Rotation Model: {has_rotation} | Current: {current_tab}"
            self.statusBar().showMessage(status)
            
        except Exception as e:
            self.statusBar().showMessage(f"Status update error: {str(e)}")
    
    # File menu methods (similar to original MainWindow)
    @pyqtSlot()
    def new_project(self):
        """Create a new project."""
        self.session.reset_project()
        self.statusBar().showMessage("New project created")
    
    @pyqtSlot()
    def open_project(self):
        """Open an existing project."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Project", ".", "JavaScript Object Notation (*.json)")
        if not file_name:
            return
        if not load_project(self.session, file_name):
            QMessageBox.critical(self, "Error", "Error occurred loading project file.")
        else:
            self.statusBar().showMessage(f"Project loaded: {path.basename(file_name)}")
    
    @pyqtSlot()
    def save_project(self):
        """Save the current project."""
        file_name: str = ""
        if self.session._project_file:
            file_name = self.session._project_file
        else:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Project", ".", "JavaScript Object Notation (*.json)")
        
        if not file_name:
            return
        if not save_project(self.session, file_name):
            QMessageBox.critical(self, "Error", "Error occurred saving project file.")
        else:
            self.statusBar().showMessage(f"Project saved: {path.basename(file_name)}")
    
    @pyqtSlot()
    def open_feature_collections(self):
        """Open feature collection files."""
        fc_filepaths, _ = QFileDialog.getOpenFileNames(self, "Open Feature Collection(s)", 
                                                       self.session._project_path if self.session._project_path else ".", 
                                                       "GPlates Markup Language (*.gpml)")
        if len(fc_filepaths) == 0:
            return
        
        self.session.load_feature_collections(fc_filepaths)
        self.statusBar().showMessage(f"Loaded {len(fc_filepaths)} feature collection(s)")
    
    @pyqtSlot()
    def open_rotation_model(self):
        """Open a rotation model file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Rotation Model", 
                                                   self.session._project_path if self.session._project_path else ".", 
                                                   "PLATES4 rotation (*.rot)")
        if file_name:
            self.session.load_rotation_model(file_name)
            self.statusBar().showMessage(f"Rotation model loaded: {path.basename(file_name)}")
    
    @pyqtSlot()
    def reload_files(self):
        """Reload all loaded files."""
        self.session.reload_features()
        self.session.reload_rotation_model()
        self.statusBar().showMessage("Files reloaded")
    
    def save_session(self):
        """Save current session state (uses project saving functionality)."""
        try:
            self.save_project()
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Error saving session: {str(e)}")
    
    def load_session(self):
        """Load saved session state (uses project loading functionality)."""
        try:
            self.open_project()
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Error loading session: {str(e)}")
    
    def show_help(self):
        """Show help documentation."""
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("GPlates Operations Help")
        help_dialog.setIcon(QMessageBox.Information)
        
        help_text = """
        <h3>GPlates Operations Suite Help</h3>
        
        <p>This suite provides three main operation categories:</p>
        
        <h4>🌋 Geological Processes</h4>
        <ul>
        <li><b>Subduction:</b> Model feature consumption through subduction zones</li>
        <li><b>Rifting:</b> Create continental rifts and split features</li>
        <li><b>Ocean Spreading:</b> Generate ocean crust from mid-ocean ridges</li>
        </ul>
        
        <h4>🌍 Plate Operations</h4>
        <ul>
        <li><b>Plate Splitting:</b> Split plates using geological features</li>
        <li><b>Line Splitting:</b> Split lines at intersections</li>
        <li><b>Polygon Operations:</b> Intersection, union, and difference operations</li>
        </ul>
        
        <h4>🔄 Rotation Management</h4>
        <ul>
        <li><b>Initialize Rotations:</b> Create rotation models from features</li>
        <li><b>Create Plates:</b> Split features into new plates</li>
        <li><b>Maintenance:</b> Fix and validate rotation models</li>
        </ul>
        
        <p><b>Getting Started:</b> Each operation provides guided workflows with numbered steps. 
        Follow the step indicators to complete operations successfully.</p>
        
        <p><b>Need more help?</b> Each tab contains detailed tooltips and contextual help.</p>
        """
        
        help_dialog.setText(help_text)
        help_dialog.setDetailedText("""
        Workflow Tips:
        
        1. Load your feature collections and rotation models first
        2. Follow the numbered workflow steps in each operation
        3. Use the filter controls to narrow down feature selections
        4. Check the append options when saving to existing files
        5. Validate your results using the rotation management tools
        
        Common Issues:
        
        - "No features selected": Make sure to select features in the tree view
        - "No rotation model": Load a rotation file before geological operations
        - "Invalid time range": Ensure start time > end time for geological time
        - "Plate ID exists": Choose a unique plate ID when creating new plates
        
        File Formats:
        
        - Features: GPlates Markup Language (.gpml)
        - Rotations: PLATES4 Rotation File (.rot)
        """)
        
        help_dialog.exec()
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
        <h2>GPlates Operations Suite</h2>
        
        <p>A geological modeling toolkit for:</p>
        <ul>
        <li>Subduction zone modeling</li>
        <li>Continental rifting simulation</li>
        <li>Ocean crust generation</li>
        <li>Plate splitting and geometric operations</li>
        <li>Rotation model management</li>
        </ul>
        
        <p><b>Features:</b></p>
        <ul>
        <li>Guided step-by-step workflows</li>
        <li>Integrated validation and error checking</li>
        <li>Rotation model tools</li>
        </ul>
        
        <p><b>Future:</b></p>
        <ul>
        <li>Topology generation capabilities</li>
        </ul>
        
        <p><b>Built with:</b> Python, PyQt5, and pygplates</p>
        
        <p style="margin-top: 20px; color: #666; font-size: 11px;">
        This software is designed for worldbuilding tectonic histories with GPlates.
        </p>
        """
        
        QMessageBox.about(self, "About GPlates Operations Suite", about_text)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up timers
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        event.accept()


if __name__ == "__main__":
    # Example usage
    import sys
    from PyQt5.QtWidgets import QApplication
    from core.session import Session
    
    app = QApplication(sys.argv)
    app.setApplicationName("GPlates Operations Suite")
    app.setOrganizationName("GPlates Modeling Tools")
    
    # Set application style
    app.setStyleSheet("""
        QTabWidget::pane {
            border: 1px solid #C0C0C0;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #f0f0f0;
            padding: 8px 16px;
            margin-right: 2px;
            border: 1px solid #C0C0C0;
            border-bottom-color: #C0C0C0;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #e6f3ff;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #C0C0C0;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px 0 10px;
        }
    """)
    
    session = Session()
    
    window = ImprovedGeologicalOperationsWindow(session)
    window.show()
    
    sys.exit(app.exec_())