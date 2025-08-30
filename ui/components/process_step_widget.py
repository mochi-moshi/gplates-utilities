"""
Process Step Widget

A visual step indicator for geological process workflows with completion and active states.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class ProcessStepWidget(QFrame):
    """A visual step indicator for the geological process workflow."""
    
    def __init__(self, step_number: int, title: str, description: str, parent=None):
        super().__init__(parent)
        self.step_number = step_number
        self.is_completed = False
        self.is_active = False
        
        self.setFrameStyle(QFrame.StyledPanel)
        
        layout = QHBoxLayout(self)
        
        # Step number circle
        self.step_label = QLabel(str(step_number))
        self.step_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                border-radius: 8px;
                color: #666;
                font-weight: bold;
                padding: 8px;
                min-width: 10px;
                max-width: 10px;
                min-height: 10px;
                max-height: 10px;
                text-align: center;
            }
        """)
        self.step_label.setAlignment(Qt.AlignCenter)
        
        # Step content
        content_layout = QVBoxLayout()
        self.title_label = QLabel(f"<b>{title}</b>")
        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #666;")
        
        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.description_label)
        
        layout.addWidget(self.step_label)
        layout.addLayout(content_layout, 1)
        
    def set_active(self, active: bool):
        """Set this step as active/current."""
        self.is_active = active
        self.update_style()
        
    def set_completed(self, completed: bool):
        """Mark this step as completed."""
        self.is_completed = completed
        self.update_style()
        
    def update_style(self):
        """Update visual styling based on state."""
        if self.is_completed:
            style = """
                QLabel {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 8px;
                    min-width: 10px;
                    max-width: 10px;
                    min-height: 10px;
                    max-height: 10px;
                }
            """
            self.step_label.setText("✓")
        elif self.is_active:
            style = """
                QLabel {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 8px;
                    min-width: 10px;
                    max-width: 10px;
                    min-height: 10px;
                    max-height: 10px;
                }
            """
            self.step_label.setText(str(self.step_number))
        else:
            style = """
                QLabel {
                    background-color: #e0e0e0;
                    border-radius: 8px;
                    color: #666;
                    font-weight: bold;
                    padding: 8px;
                    min-width: 10px;
                    max-width: 10px;
                    min-height: 10px;
                    max-height: 10px;
                }
            """
            self.step_label.setText(str(self.step_number))
            
        self.step_label.setStyleSheet(style)