from os import path
from PySide6.QtCore import Slot
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTreeView, QVBoxLayout, QWidget

from core.rotations import create_initial_rotations, create_new_rotation_plate, replace_final_rotation
from core.session import Session
from models.polygon_filter_model import PolygonFilterModel
from ui.decorators.time_decorator_delegate import TimeDecoratorDelegate

from pygplates import FeatureCollection

class RotationHelperWindow(QWidget):
    def __init__(self, session: Session):
        super().__init__()

        self.session = session
        self._feature_save_location: str = ""
        self._rotation_save_location: str = ""

        self.feature_model = PolygonFilterModel()
        self.feature_model.setSourceModel(session.get_feature_model())
        
        self.setWindowTitle("Rotation Helper Tool")
        self.resize(900, 400)

        split_date_label = QLabel("Split Time:")
        self.split_time = QLineEdit()
        self.split_time.setValidator(QDoubleValidator())
        self.split_time.editingFinished.connect(self.update_split_time)

        plate_id_label = QLabel("Plate ID(s):")
        self.plate_filter = QLineEdit()
        self.plate_filter.setValidator(QRegularExpressionValidator("\\d+(,\\d*)*"))
        self.plate_filter.editingFinished.connect(self.update_plate_filter)
        
        new_plate_id_label = QLabel("New Plate ID:")
        self.new_plate_id = QLineEdit()
        self.new_plate_id.setValidator(QRegularExpressionValidator("\\d+"))

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
        

        set_feature_save_location_button = QPushButton("Set Feature Save Location")
        set_feature_save_location_button.clicked.connect(self.set_feature_save_location)
        
        set_rotation_save_location_button = QPushButton("Set Rotation Save Location")
        set_rotation_save_location_button.clicked.connect(self.set_rotation_save_location)

        reset_rotations_button = QPushButton("Initialize/Reset Rotations")
        reset_rotations_button.clicked.connect(self.reset_rotations)
        
        fix_final_rotation_button = QPushButton("Fix Final Rotation")
        fix_final_rotation_button.clicked.connect(self.fix_final_rotation)
        
        split_features_new_plate_button = QPushButton("Split Features to New Plate")
        split_features_new_plate_button.clicked.connect(self.split_features_new_plate)

        split_time_layout = QHBoxLayout()
        split_time_layout.addWidget(split_date_label, 0)
        split_time_layout.addWidget(self.split_time, 1)

        plate_filter_layout = QHBoxLayout()
        plate_filter_layout.addWidget(plate_id_label, 0)
        plate_filter_layout.addWidget(self.plate_filter, 1)

        new_plate_id_layout = QHBoxLayout()
        new_plate_id_layout.addWidget(new_plate_id_label, 0)
        new_plate_id_layout.addWidget(self.new_plate_id, 1)

        side_layout = QVBoxLayout()
        side_layout.addLayout(split_time_layout)
        side_layout.addLayout(plate_filter_layout)
        side_layout.addWidget(QWidget(), 1)
        side_layout.addLayout(new_plate_id_layout)
        side_layout.addWidget(QWidget(), 1)
        side_layout.addWidget(set_feature_save_location_button, 0)
        side_layout.addWidget(set_rotation_save_location_button, 0)
        side_layout.addWidget(reset_rotations_button, 0)
        side_layout.addWidget(fix_final_rotation_button, 0)
        side_layout.addWidget(split_features_new_plate_button, 0)
        
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.new_feature_view, 1)
        main_layout.addLayout(side_layout, 0)

        self.setLayout(main_layout)
    
    @Slot()
    def set_feature_save_location(self):
        self._feature_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
        
    @Slot()
    def set_rotation_save_location(self):
        self._rotation_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "PLATES4 Rotation File (*.rot)")

    @Slot()
    def update_split_time(self):
        time = float(self.split_time.text())
        self.feature_model.setTimeFilter(time)
    
    @Slot()
    def update_plate_filter(self):
        filter_text = self.plate_filter.text()
        if filter_text == "":
            self.feature_model.setPlateIdFilter([])
        self.feature_model.setPlateIdFilter([id for id in filter_text.split(",") if len(id) > 0])

    @Slot()
    def reset_rotations(self):
        if self.split_time.text() == "":
            QMessageBox.critical(self, "Error", "No split time set!")
            return
          
        split_time = float(self.split_time.text())
          
        selected_feature_ids = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 7]
        selected_feature_collections = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 8]
        
        selected_features = []
        
        for i in range(len(selected_feature_ids)):
            fc = next(filter(lambda x: x.shortname == selected_feature_collections[i], self.session.loaded_feature_collections)).feature_collection
            feature = fc.get(lambda f: f.get_feature_id().get_string() == selected_feature_ids[i])
            selected_features.append(feature)
        
        if len(selected_features) == 0:
            selected_features = [f for lfc in self.session.loaded_feature_collections for f in lfc.feature_collection]
        
        if not self._rotation_save_location:
            self._rotation_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "PLATES4 Rotation File (*.rot)")
            if  not self._rotation_save_location:
              QMessageBox.critical(self, "Error", "No rotation save location set!")
              return

        fc = create_initial_rotations(selected_features, split_time, 0)
        
        if path.exists(self._rotation_save_location):
          fc2 = FeatureCollection(self._rotation_save_location)
          for f in fc:
            fc2.add(f)
          fc = fc2
        fc.write(self._rotation_save_location)
        
        if not self.session._rotationModel:
            self.session.load_rotation_model(self._rotation_save_location)
            QMessageBox.information(self, "Success", "Successfully created and loaded initial rotation file: " + path.realpath(self._rotation_save_location))
        else:
            QMessageBox.information(self, "Success", "Successfully created initial rotation file: " + path.realpath(self._rotation_save_location))

    @Slot()
    def fix_final_rotation(self):
        if not self.session._rotationModel:
            QMessageBox.critical(self, "Error", "No rotation model selected!")
            return
          
        if not self._rotation_save_location:
            self._rotation_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "PLATES4 Rotation File (*.rot)")
            if  not self._rotation_save_location:
              QMessageBox.critical(self, "Error", "No rotation save location set!")
              return

        fc = replace_final_rotation(self.session._rotationFeatureCollection)
        fc.write(self._rotation_save_location)
        
        QMessageBox.information(self, "Success", "Successfully fixed rotation file: " + path.realpath(self._rotation_save_location))

    @Slot()
    def split_features_new_plate(self):
        if self.split_time.text() == "":
            QMessageBox.critical(self, "Error", "No split time set!")
            return
          
        split_time = float(self.split_time.text())
        
        if self.new_plate_id.text() == "":
            QMessageBox.critical(self, "Error", "No new plate id set!")
            return

        new_plate_id = int(self.new_plate_id.text())
          
        selected_feature_ids = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 7]
        selected_feature_collections = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 8]
        
        selected_features = []
        
        for i in range(len(selected_feature_ids)):
            fc = next(filter(lambda x: x.shortname == selected_feature_collections[i], self.session.loaded_feature_collections)).feature_collection
            feature = fc.get(lambda f: f.get_feature_id().get_string() == selected_feature_ids[i])
            selected_features.append(feature)
        
        if len(selected_features) == 0:
            QMessageBox.critical(self, "Error", "No features selected!")
            return

        all_ids = set([f.get_reconstruction_plate_id() for lfc in self.session.loaded_feature_collections for f in lfc.feature_collection])
        if new_plate_id in all_ids:
            QMessageBox.warning(self, "Duplicate Id", "Plate Id already exists")
            return
        
        if not self.session._rotationModel:
            QMessageBox.critical(self, "Error", "No rotation model selected!")
            return
          
        if not self._feature_save_location:
            self._feature_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
            if not self._feature_save_location:
              QMessageBox.critical(self, "Error", "No feature save location set!")
              return
          
        if not self._rotation_save_location:
            self._rotation_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "PLATES4 Rotation File (*.rot)")
            if  not self._rotation_save_location:
              QMessageBox.critical(self, "Error", "No rotation save location set!")
              return

        fc, rc = create_new_rotation_plate(selected_features, self.session._rotationFeatureCollection, new_plate_id, split_time)
        if path.exists(self._rotation_save_location):
          rc2 = FeatureCollection(self._rotation_save_location)
          for f in fc:
            rc2.add(f)
          rc = rc2
        if path.exists(self._feature_save_location):
          fc2 = FeatureCollection(self._feature_save_location)
          for f in fc:
            fc2.add(f)
          fc = fc2
        fc.write(self._feature_save_location)
        rc.write(self._rotation_save_location)
        
        QMessageBox.information(self, "Success", "Successfully saved rotation file: " + path.realpath(self._rotation_save_location) + " and feature file: " + path.realpath(self._feature_save_location))