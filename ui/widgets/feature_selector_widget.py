"""
Feature Selector Widget

A widget for selecting geological features with filtering and preview capabilities.
"""

from PySide6.QtCore import Signal, QItemSelection
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView, QTreeView, QVBoxLayout, QWidget,
    QGroupBox, QFormLayout, QLineEdit, QLabel
)

from core.session import Session, FeatureDataColumn, extractFeatureDataFromRow
from models.time_range_filter_model import TimeRangeFilterModel
from ui.delegates.time_decorator_delegate import TimeDecoratorDelegate


class FeatureSelectorWidget(QWidget):
    """Enhanced feature selector with filtering and preview."""
    
    selectionChanged = Signal(int)  # number of features selected
    
    def __init__(self, session: Session, single_selection: bool = False, single_plate_id: bool = False, parent=None):
        super().__init__(parent)
        self.session = session
        self._updating_filters = False
        self._single_plate_id = single_plate_id
        
        self.setup_ui(single_selection)
        self.connect_signals()
        
    def setup_ui(self, single_selection: bool):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Filter controls
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout(filter_group)
        
        self.plate_filter = QLineEdit()
        self.plate_filter.setPlaceholderText("e.g., 701,801,802")
        self.plate_filter.setValidator(QRegularExpressionValidator("\\d+(,\\s*\\d+)*"))
        
        filter_layout.addRow("Plate IDs:", self.plate_filter)
        
        # Feature view
        self.feature_model = TimeRangeFilterModel()
        self.feature_model.setSourceModel(self.session.get_feature_model())
        
        self.feature_view = QTreeView()
        self.feature_view.setModel(self.feature_model)
        self.feature_view.setColumnHidden(FeatureDataColumn.feature_name_and_id, True)  # Hide internal columns
        self.feature_view.setColumnHidden(FeatureDataColumn.geometry_type, True)
        self.feature_view.setColumnHidden(FeatureDataColumn.reconstruction_method, True)
        self.feature_view.setColumnHidden(FeatureDataColumn.left_plate, True)
        self.feature_view.setColumnHidden(FeatureDataColumn.right_plate, True)
        self.feature_view.setItemDelegateForColumn(FeatureDataColumn.start_time, TimeDecoratorDelegate(self.feature_view))
        self.feature_view.setItemDelegateForColumn(FeatureDataColumn.end_time, TimeDecoratorDelegate(self.feature_view))
        self.feature_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection if single_selection else QAbstractItemView.SelectionMode.MultiSelection)
        self.feature_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Selection info
        self.selection_label = QLabel("No features selected")
        self.selection_label.setStyleSheet("color: #666; font-size: 11px;")
        
        layout.addWidget(filter_group)
        layout.addWidget(QLabel("<b>Available Features:</b>"))
        layout.addWidget(self.feature_view)
        layout.addWidget(self.selection_label)
        
    def connect_signals(self):
        """Connect widget signals."""
        self.plate_filter.editingFinished.connect(self.update_plate_filter)
        self.feature_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
    def update_plate_filter(self):
        """Update the plate ID filter."""
        if self._updating_filters:
            return
            
        self._updating_filters = True
        try:
            if self._single_plate_id:
              selected_rows = set([self.feature_model.mapToSource(i).row() for i in self.feature_view.selectedIndexes()])
              selected_feature_data = [extractFeatureDataFromRow(self.feature_model.sourceModel(), row_num) for row_num in selected_rows]
              selected_main_ids = set()
              selected_half_ids = set()
              for data in selected_feature_data:
                if data.reconstruction_method == 'ByPlateId':
                  selected_main_ids.add(data.plate_id)
                else:
                  selected_half_ids.add(data.left_plate)
                  selected_half_ids.add(data.right_plate)

              selected_ids = [i for i in selected_main_ids]
              if not selected_ids:
                selected_ids = [i for i in selected_half_ids]
            else:
              selected_ids = []
            
            filter_text = self.plate_filter.text().strip()
            if filter_text:
                plate_ids = selected_ids + [id.strip() for id in filter_text.split(",") if id.strip()]
                self.feature_model.setPlateIdFilter(plate_ids)
            else:
                self.feature_model.setPlateIdFilter(selected_ids)
        finally:
            self._updating_filters = False
    
    def set_time_filter(self, start_time: float, end_time: float):
        """Set the time range filter."""
        self._updating_filters = True
        try:
            self.feature_model.setTimeRangeFilter(start_time, end_time)
        finally:
            self._updating_filters = False
    
    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        """Handle selection changes."""
        selection_count = len(self.feature_view.selectedIndexes()) // self.feature_model.columnCount()
        self.selection_label.setText(f"{selection_count} features selected")
        if self._single_plate_id and not (selected.isEmpty() and deselected.isEmpty()):
          self.update_plate_filter()
        self.selectionChanged.emit(selection_count)
    
    def get_selected_features(self):
        """Get list of selected features."""
        selected_indexes = self.feature_view.selectedIndexes()
        selected_feature_ids = [i.data() for i in selected_indexes if i.column() == FeatureDataColumn.feature_id]
        selected_feature_collections = [i.data() for i in selected_indexes if i.column() == FeatureDataColumn.feature_collection]
        
        selected_features = []
        for i in range(len(selected_feature_ids)):
            fc = next(filter(lambda x: x.shortname == selected_feature_collections[i], 
                           self.session.loaded_feature_collections)).feature_collection
            feature = fc.get(lambda f: f.get_feature_id().get_string() == selected_feature_ids[i])
            if feature:
                selected_features.append(feature)
        
        return selected_features
    
    def clear_selection(self):
        """Clear current feature selection."""
        self.feature_view.clearSelection()
        
    def select_all(self):
        """Select all visible features."""
        self.feature_view.selectAll()