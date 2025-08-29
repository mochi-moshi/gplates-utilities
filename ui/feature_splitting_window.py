from os import path
from PySide6.QtCore import Slot
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTreeView, QVBoxLayout, QWidget

from core.plate_splitter import split_plate_features
from core.session import Session
from models.splitter_filter_model import SplitterFilterModel
from models.polygon_filter_model import PolygonFilterModel
from ui.decorators.time_decorator_delegate import TimeDecoratorDelegate

from pygplates import FeatureCollection

class FeatureSplittingWindow(QWidget):
    def __init__(self, session: Session):
        super().__init__()

        self.session = session
        self._save_location: str = ""
        self._lines_only: bool = False

        self.splitter_model = SplitterFilterModel()
        self.splitter_model.setFeatureTypeFilter([])
        self.splitter_model.setSourceModel(session.get_feature_model())

        self.feature_model = PolygonFilterModel()
        self.feature_model.setSourceModel(session.get_feature_model())
        
        self.setWindowTitle("Plate Splitting Tool")
        self.resize(900, 400)

        split_date_label = QLabel("Split Time:")
        self.split_time = QLineEdit()
        self.split_time.setValidator(QDoubleValidator())
        self.split_time.editingFinished.connect(self.update_split_time)

        plate_id_label = QLabel("Plate ID(s):")
        self.plate_filter = QLineEdit()
        self.plate_filter.setValidator(QRegularExpressionValidator("\\d+(,\\d*)*"))
        self.plate_filter.editingFinished.connect(self.update_plate_filter)
        
        self.splitter_selection = QComboBox()
        self.splitter_selection.setModel(self.splitter_model)
        self.splitter_selection.setModelColumn(1)
        self.splitter_selection.setPlaceholderText("Select splitter feature ...")
        
        line_splitters_only_label = QLabel("Lines Only")
        self.line_splitters_only = QCheckBox()
        self.line_splitters_only.checkStateChanged.connect(self.update_line_splitters_only)

        self.new_feature_view = QTreeView()
        self.new_feature_view.setModel(self.feature_model)
        self.new_feature_view.setColumnHidden(1, True)
        self.new_feature_view.setColumnHidden(3, True)
        self.new_feature_view.setItemDelegateForColumn(5, TimeDecoratorDelegate(self.new_feature_view))
        self.new_feature_view.setItemDelegateForColumn(6, TimeDecoratorDelegate(self.new_feature_view))
        self.new_feature_view.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.new_feature_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.new_feature_view.setStyleSheet(
            """
            QTreeView::branch  {
                background: palette(base);
            }

            QTreeView::branch:selected {
                background-color: rgb(34, 177, 76);
            }
            """)    # Sets
        self.new_feature_view.clicked.connect(self.on_item_changed)

        set_save_location_button = QPushButton("Set Save Location")
        set_save_location_button.clicked.connect(self.set_save_location)

        split_button = QPushButton("Split")
        split_button.clicked.connect(self.on_split)

        split_time_layout = QHBoxLayout()
        split_time_layout.addWidget(split_date_label, 0)
        split_time_layout.addWidget(self.split_time, 1)

        plate_filter_layout = QHBoxLayout()
        plate_filter_layout.addWidget(plate_id_label, 0)
        plate_filter_layout.addWidget(self.plate_filter, 1)
        
        line_splitters_only_layout = QHBoxLayout()
        line_splitters_only_layout.addWidget(line_splitters_only_label, 1)
        line_splitters_only_layout.addWidget(self.line_splitters_only, 0)

        side_layout = QVBoxLayout()
        side_layout.addLayout(split_time_layout)
        side_layout.addLayout(plate_filter_layout)
        side_layout.addLayout(line_splitters_only_layout)
        side_layout.addWidget(self.splitter_selection)
        side_layout.addWidget(QWidget(), 1)
        side_layout.addWidget(set_save_location_button, 0)
        side_layout.addWidget(split_button, 0)
        
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.new_feature_view, 1)
        main_layout.addLayout(side_layout, 0)

        self.setLayout(main_layout)

    @Slot()
    def on_item_changed(self):
      self.splitter_model.setFeatureIdFilter([i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 6])
    
    @Slot()
    def set_save_location(self):
        self._save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")

    @Slot()
    def update_split_time(self):
        time = float(self.split_time.text())
        self.splitter_model.setTimeFilter(time)
        self.feature_model.setTimeFilter(time)
    
    @Slot()
    def update_plate_filter(self):
        filter_text = self.plate_filter.text()
        if filter_text == "":
            self.feature_model.setPlateIdFilter([])
        self.feature_model.setPlateIdFilter([id for id in filter_text.split(",") if len(id) > 0])

    @Slot()
    def update_line_splitters_only(self):
      self._lines_only = self.line_splitters_only.isChecked()
      self.splitter_model.setFeatureTypeFilter(["ContinentalRift", "SubductionZone"] if self._lines_only else [])

    @Slot()
    def on_split(self):
        if self.splitter_selection.currentIndex() < 0:
            QMessageBox.critical(self, "Error", "No rift selected!")
            return
        
        splitter_idx = self.splitter_model.index(self.splitter_selection.currentIndex(), 7)
        all_features = [f for lfc in self.session.loaded_feature_collections for f in lfc.feature_collection]
        selected_splitter = next(filter(lambda f: f.get_feature_id().get_string() == self.splitter_model.itemData(splitter_idx)[0], all_features))
        
        if self.split_time.text() == "":
            QMessageBox.critical(self, "Error", "No split time set!")
            return

        split_time = float(self.split_time.text())

        if selected_splitter == None:
            QMessageBox.critical(self, "Error", "No splitter selected!")
            return
        
        
        selected_feature_ids = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 7]
        selected_feature_collections = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 8]
        
        selected_features = []

        for i in range(len(selected_feature_ids)):
            fc = next(filter(lambda x: x.shortname == selected_feature_collections[i],self.session.loaded_feature_collections)).feature_collection
            feature = fc.get(lambda f: f.get_feature_id().get_string() == selected_feature_ids[i])
            selected_features.append(feature)
        
        if len(selected_features) == 0:
            QMessageBox.critical(self, "Error", "No features selected!")
            return
        
        if not self.session._rotationModel:
            QMessageBox.critical(self, "Error", "No rotation model selected!")
            return
        
        if not self._save_location:
            QMessageBox.critical(self, "Error", "No save location set!")
            return

        fc = split_plate_features(selected_features, selected_splitter, self.session._rotationModel, split_time)

        if path.exists(self._save_location):
          fc2 = FeatureCollection(self._save_location)
          for f in fc:
            fc2.add(f)
          fc = fc2
        fc.write(self._save_location)
        QMessageBox.information(self, "Success", "Successfully saved split features: " + path.realpath(self._save_location))
