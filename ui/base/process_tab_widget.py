"""
Process Tab Base Widget

Base class for geological process tabs with common workflow functionality.
"""

from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QFrame
from core.session import Session
from pygplates import FeatureCollection


class ProcessTabWidget(QWidget):
    """Base class for geological process tabs."""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setup_ui()
        self.setup_workflow()

    def wrap_in_scroll_area(self, content_widget: QWidget) -> QScrollArea:
        """
        Wrap a widget in a scroll area for scrollable content.

        Args:
            content_widget: The widget to wrap

        Returns:
            QScrollArea containing the widget
        """
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        return scroll_area

    def setup_ui(self):
        """Setup the UI components - to be implemented by subclasses."""
        pass

    def setup_workflow(self):
        """Setup workflow steps - to be implemented by subclasses."""
        pass

    def validate_inputs(self) -> tuple[bool, str]:
        """Validate all inputs - to be implemented by subclasses."""
        return True, "Inputs are valid"

    def process(self) -> FeatureCollection:
        """Execute the geological process - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process method")

    def update_step_status(self, step_index: int, completed: bool):
        """Update the status of a workflow step."""
        if hasattr(self, "steps") and 0 <= step_index < len(self.steps):
            self.steps[step_index].set_completed(completed)

            # Set next step as active if current step is completed
            if completed and step_index + 1 < len(self.steps):
                self.steps[step_index + 1].set_active(True)

            # Clear active status from previous steps
            if completed:
                for i, step in enumerate(self.steps):
                    if i != step_index and i != step_index + 1:
                        step.set_active(False)
