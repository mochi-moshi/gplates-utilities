"""
Operation Summary Widget

A clickable widget showing a summary of available operations in a category.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


class OperationSummaryWidget(QFrame):
    """Widget showing a summary of available operations in each category."""
    
    def __init__(self, title: str, description: str, operations: list[str], icon: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui(title, description, operations, icon)
        
    def setup_ui(self, title: str, description: str, operations: list[str], icon: str):
        """Setup the UI components."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #f9f9f9;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #2196F3;
                background-color: #f0f8ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 24px; padding: 5px;")
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setStyleSheet("font-size: 14px; color: #333;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Operations list
        ops_label = QLabel("<b>Available Operations:</b>")
        ops_label.setStyleSheet("color: #333; font-size: 12px;")
        layout.addWidget(ops_label)
        
        for op in operations:
            op_label = QLabel(f"• {op}")
            op_label.setStyleSheet("color: #555; font-size: 11px; margin-left: 10px;")
            layout.addWidget(op_label)
        
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        """Handle click events."""
        if event.button() == Qt.LeftButton:
            # Emit a custom signal or call parent method if it exists
            if hasattr(self.parent(), 'select_operation_category'):
                self.parent().select_operation_category(self)
        super().mousePressEvent(event)