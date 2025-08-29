from os import path
from PySide6.QtCore import Slot
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTreeView, QVBoxLayout, QWidget, QCheckBox

from core.polygon_operations import join_plate_features_by_intersect, join_plate_features_by_union, split_plate_features_by_difference
from core.session import Session
from models.polygon_filter_model import PolygonFilterModel
from ui.decorators.time_decorator_delegate import TimeDecoratorDelegate

class PolygonOperationWindow(QWidget):
    def __init__(self, session: Session):
        super().__init__()

        self.session = session
        self._save_location: str = ""
        self._new_plate_id: int = 0
        self._duplicate_per_plate: bool = False

        self.feature_model = PolygonFilterModel()
        self.feature_model.setSourceModel(session.get_feature_model())
        
        self.setWindowTitle("Polygon Operation Tool")
        self.resize(900, 400)

        split_date_label = QLabel("Split Time:")
        self.split_time = QLineEdit()
        self.split_time.setValidator(QDoubleValidator())
        self.split_time.textEdited.connect(self.update_split_time)

        plate_id_label = QLabel("Plate ID(s):")
        self.plate_filter = QLineEdit()
        self.plate_filter.setValidator(QRegularExpressionValidator("\\d+(,\\d*)*"))
        self.plate_filter.textEdited.connect(self.update_plate_filter)
        
        new_plate_id_label = QLabel("New Plate ID:")
        self.new_plate_id = QLineEdit()
        self.new_plate_id.setValidator(QRegularExpressionValidator("\\d+"))
        self.new_plate_id.textEdited.connect(self.update_new_plate_id)
        self.new_plate_id.setText(str(self._new_plate_id))

        duplicate_per_plate_label = QLabel("Duplicate Per Plate")
        self.duplicate_per_plate = QCheckBox()
        self.duplicate_per_plate.checkStateChanged.connect(self.update_duplicate_per_plate)

        self.new_feature_view = QTreeView()
        self.new_feature_view.setModel(self.feature_model)
        self.new_feature_view.setColumnHidden(2, True)
        self.new_feature_view.setItemDelegateForColumn(4, TimeDecoratorDelegate(self.new_feature_view))
        self.new_feature_view.setItemDelegateForColumn(5, TimeDecoratorDelegate(self.new_feature_view))
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

        set_save_location_button = QPushButton("Set Save Location")
        set_save_location_button.clicked.connect(self.set_save_location)

        intersection_button = QPushButton("Intersection")
        intersection_button.clicked.connect(self.on_intersection)
        
        difference_button = QPushButton("Difference")
        difference_button.clicked.connect(self.on_difference)
        
        union_button = QPushButton("Union")
        union_button.clicked.connect(self.on_union)

        split_time_layout = QHBoxLayout()
        split_time_layout.addWidget(split_date_label, 0)
        split_time_layout.addWidget(self.split_time, 1)

        plate_filter_layout = QHBoxLayout()
        plate_filter_layout.addWidget(plate_id_label, 0)
        plate_filter_layout.addWidget(self.plate_filter, 1)

        new_plate_id_layout = QHBoxLayout()
        new_plate_id_layout.addWidget(new_plate_id_label, 0)
        new_plate_id_layout.addWidget(self.new_plate_id, 1)

        duplicate_per_plate_layout = QHBoxLayout()
        duplicate_per_plate_layout.addWidget(duplicate_per_plate_label, 1)
        duplicate_per_plate_layout.addWidget(self.duplicate_per_plate, 0)

        side_layout = QVBoxLayout()
        side_layout.addLayout(split_time_layout)
        side_layout.addLayout(plate_filter_layout)
        side_layout.addWidget(QWidget(), 1)
        side_layout.addLayout(new_plate_id_layout)
        side_layout.addLayout(duplicate_per_plate_layout)
        side_layout.addWidget(QWidget(), 1)
        side_layout.addWidget(set_save_location_button, 0)
        side_layout.addWidget(intersection_button, 0)
        side_layout.addWidget(difference_button, 0)
        side_layout.addWidget(union_button, 0)
        
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.new_feature_view, 1)
        main_layout.addLayout(side_layout, 0)

        self.setLayout(main_layout)
    
    @Slot()
    def set_save_location(self):
        self._save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")

    @Slot()
    def update_split_time(self):
        time = float(self.split_time.text() or 'inf')
        self.feature_model.setTimeFilter(time)
    
    @Slot()
    def update_plate_filter(self):
        filter_text = self.plate_filter.text()
        self.feature_model.setPlateIdFilter([id for id in filter_text.split(",") if len(id) > 0])
            
    @Slot()
    def update_new_plate_id(self):
        filter_text = self.new_plate_id.text()
        if filter_text == "":
            self._new_plate_id = 0
            self.new_plate_id.setText(str(self._new_plate_id))
        else:
            self._new_plate_id = int(filter_text)
            
    @Slot()
    def update_duplicate_per_plate(self):
        self._duplicate_per_plate = self.duplicate_per_plate.isChecked()
        self.new_plate_id.setDisabled(self._duplicate_per_plate)

    @Slot()
    def on_intersection(self):
        if self.split_time.text() == "":
            QMessageBox.critical(self, "Error", "No split time set!")
            return

        split_time = float(self.split_time.text())
        
        selected_feature_ids = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 6]
        selected_feature_collections = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 7]
        
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
            self._save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
            
            if not self._save_location:
                QMessageBox.critical(self, "Error", "No save location set!")
                return

        fc = join_plate_features_by_intersect(selected_features, self.session._rotationModel, split_time, reconstruction_plate_id=self._new_plate_id if not self._duplicate_per_plate else None)

        if len(fc) == 0:
            QMessageBox.information(self, "No Action", "All of the plates do not intersect")
            return
        fc.write(self._save_location)
        QMessageBox.information(self, "Success", "Successfully saved split features: " + path.realpath(self._save_location))
  
    @Slot()
    def on_difference(self):
        if self.split_time.text() == "":
            QMessageBox.critical(self, "Error", "No split time set!")
            return

        split_time = float(self.split_time.text())
        
        selected_feature_ids = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 6]
        selected_feature_collections = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 7]
        
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
            self._save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
            
            if not self._save_location:
                QMessageBox.critical(self, "Error", "No save location set!")
                return

        fc = split_plate_features_by_difference(selected_features, self.session._rotationModel, split_time, reconstruction_plate_id=self._new_plate_id if not self._duplicate_per_plate else None)

        if len(fc) == 0:
            QMessageBox.information(self, "No Action", "All of the plates overlap each other")
            return
        fc.write(self._save_location)
        QMessageBox.information(self, "Success", "Successfully saved split features: " + path.realpath(self._save_location))
  
    @Slot()
    def on_union(self):
        if self.split_time.text() == "":
            QMessageBox.critical(self, "Error", "No split time set!")
            return

        split_time = float(self.split_time.text())
        
        selected_feature_ids = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 6]
        selected_feature_collections = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 7]
        
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
            self._save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
            
            if not self._save_location:
                QMessageBox.critical(self, "Error", "No save location set!")
                return

        fc = join_plate_features_by_union(selected_features, self.session._rotationModel, split_time, reconstruction_plate_id=self._new_plate_id if not self._duplicate_per_plate else None)

        if len(fc) == 0:
            QMessageBox.critical(self, "Error", "Union returned no geometry")
            return
        fc.write(self._save_location)
        QMessageBox.information(self, "Success", "Successfully saved split features: " + path.realpath(self._save_location))
