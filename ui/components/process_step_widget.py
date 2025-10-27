"""
Process Step Widget

A visual step indicator for geological process workflows with completion and active states.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QSizePolicy,
    QLayout,
)


class ProcessStepWidget(QFrame):
    """A visual step indicator for the geological process workflow."""

    def __init__(self, step_number: int, title: str, description: str, parent=None):
        super().__init__(parent)
        self.step_number = step_number
        self.is_completed = False
        self.is_active = False

        self.setFrameStyle(QFrame.StyledPanel)

        layout = QHBoxLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        # Step number circle
        self.step_label = QLabel(str(step_number))
        self.step_label.setStyleSheet(
            """
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
        """
        )
        self.step_label.setAlignment(Qt.AlignCenter)

        # Step content
        content_layout = QVBoxLayout()
        content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.title_label = QLabel(f"<b>{title}</b>")
        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)

        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.description_label)

        layout.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.step_label)
        layout.addLayout(content_layout, 1)

        self.setLayout(layout)
        self.setMinimumSize(layout.minimumSize())
        # self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)

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
