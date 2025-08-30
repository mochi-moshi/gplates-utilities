"""
Welcome Tab Widget

A reusable welcome tab with operation overview and quick access functionality.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel

from ui.components.operation_summary_widget import OperationSummaryWidget


class WelcomeTabWidget(QWidget):
    """Welcome tab with operation overview and quick access."""
    
    operationSelected = Signal(str)  # operation category name
    
    def __init__(self, title: str = "Geological Operations Suite", 
                 description: str = None, operations_config: list[dict] = None, parent=None):
        super().__init__(parent)
        self.title = title
        self.description = description or self.default_description()
        self.operations_config = operations_config or self.default_operations_config()
        self.setup_ui()
        
    def default_description(self) -> str:
        """Default welcome description."""
        return """
        Welcome to the comprehensive geological modeling toolkit. This interface provides
        access to all geological operations including subduction modeling, plate operations,
        and rotation management through intuitive, guided workflows.
        """
        
    def default_operations_config(self) -> list[dict]:
        """Default operations configuration."""
        return [
            {
                "title": "Geological Processes",
                "description": "Model geological processes through time including subduction, rifting, and ocean spreading.",
                "operations": [
                    "Subduction Zone Processing",
                    "Continental Rifting", 
                    "Ocean Crust Generation",
                    "Mid-Ocean Ridge Spreading",
                    "Topology Generation"
                ],
                "icon": "🌋",
                "key": "Geological Processes"
            },
            {
                "title": "Plate Operations",
                "description": "Perform various operations on tectonic plates including splitting and geometric operations.",
                "operations": [
                    "Plate Splitting",
                    "Line Intersection Splitting",
                    "Polygon Intersection", 
                    "Polygon Union",
                    "Polygon Difference"
                ],
                "icon": "🌍", 
                "key": "Plate Operations"
            },
            {
                "title": "Rotation Management",
                "description": "Manage plate rotation models including initialization, plate creation, and maintenance.",
                "operations": [
                    "Initialize Rotation Models",
                    "Create New Plates",
                    "Fix Final Rotations",
                    "Model Validation",
                    "Rotation Maintenance"
                ],
                "icon": "🔄",
                "key": "Rotation Management"
            }
        ]
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Welcome header
        welcome_label = QLabel(f"""
        <h1>{self.title}</h1>
        <p style="font-size: 14px; color: #666;">
        {self.description}
        </p>
        """)
        welcome_label.setWordWrap(True)
        welcome_label.setStyleSheet("padding: 20px; background-color: #f0f8ff; border-radius: 8px; margin-bottom: 20px;")
        
        layout.addWidget(welcome_label)
        
        # Operation categories
        categories_label = QLabel("<h2>Operation Categories</h2>")
        layout.addWidget(categories_label)
        
        # Create operation summary widgets
        categories_layout = QGridLayout()
        
        self.operation_widgets = {}
        
        for i, config in enumerate(self.operations_config):
            widget = OperationSummaryWidget(
                config["title"],
                config["description"], 
                config["operations"],
                config.get("icon", "")
            )
            
            # Store reference for event handling
            self.operation_widgets[config["key"]] = widget
            
            # Add to grid layout (2 columns)
            row = i // 2
            col = i % 2
            if len(self.operations_config) == 3 and i == 2:
                # Special case for 3 items - put last one spanning both columns
                categories_layout.addWidget(widget, row, 0, 1, 2)
            else:
                categories_layout.addWidget(widget, row, col)
        
        layout.addLayout(categories_layout)
        
        # Quick start section
        self.add_quick_start_section(layout)
        
        layout.addStretch()
        
    def add_quick_start_section(self, layout):
        """Add quick start section to layout."""
        quick_start_label = QLabel("<h3>Quick Start</h3>")
        layout.addWidget(quick_start_label)
        
        quick_start_text = QLabel("""
        <p><b>New to geological modeling?</b> Start with the <b>Geological Processes</b> tab to model 
        fundamental geological processes like subduction and rifting.</p>
        
        <p><b>Working with existing data?</b> Use the <b>Plate Operations</b> tab to split plates 
        and perform geometric operations on your features.</p>
        
        <p><b>Need rotation models?</b> The <b>Rotation Management</b> tab provides comprehensive 
        tools for creating and maintaining plate rotation models.</p>
        
        <p style="margin-top: 15px; padding: 10px; background-color: #fff3cd; border-radius: 5px; border-left: 4px solid #ffc107;">
        <b>💡 Tip:</b> Each tab provides guided workflows with step-by-step instructions. 
        Look for the numbered workflow steps at the top of each operation.
        </p>
        """)
        quick_start_text.setWordWrap(True)
        quick_start_text.setStyleSheet("color: #333; line-height: 1.4;")
        
        layout.addWidget(quick_start_text)
    
    def select_operation_category(self, widget):
        """Handle operation category selection."""
        for key, stored_widget in self.operation_widgets.items():
            if stored_widget == widget:
                self.operationSelected.emit(key)
                break