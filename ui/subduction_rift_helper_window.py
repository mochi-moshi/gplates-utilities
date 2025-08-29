from os import path
from PySide6.QtCore import Slot
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTreeView, QVBoxLayout, QWidget

from core.session import Session
from core.worldbuilding import diverge, rift, subduct
from models.line_filter_model import LineFilterModel
from models.time_range_filter_model import TimeRangeFilterModel
from ui.decorators.time_decorator_delegate import TimeDecoratorDelegate

from pygplates import FeatureType, FeatureCollection

class SubductionRiftHelperWindow(QWidget):
    def __init__(self, session: Session):
        super().__init__()

        self.session = session
        self._feature_save_location: str = ""
        self._rotation_save_location: str = ""

        self.feature_model = TimeRangeFilterModel()
        self.feature_model.setSourceModel(session.get_feature_model())
        
        self.splitter_model = LineFilterModel()
        self.splitter_model.setFeatureTypeFilter(["ContinentalRift", "SubductionZone", 'MidOceanRidge'])
        self.splitter_model.setSourceModel(session.get_feature_model())
        
        self.setWindowTitle("Subduction/Rift Helper Tool")
        self.resize(900, 400)

        start_date_label = QLabel("Start Time:")
        self.start_time = QLineEdit()
        self.start_time.setValidator(QDoubleValidator())
        self.start_time.editingFinished.connect(self.update_start_time)
        end_date_label = QLabel("End Time:")
        self.end_time = QLineEdit()
        self.end_time.setValidator(QDoubleValidator())
        self.end_time.editingFinished.connect(self.update_end_time)

        plate_id_label = QLabel("Plate ID(s):")
        self.plate_filter = QLineEdit()
        self.plate_filter.setValidator(QRegularExpressionValidator("\\d+(,\\d*)*"))
        self.plate_filter.editingFinished.connect(self.update_plate_filter)
        
        self.splitter_selection = QComboBox()
        self.splitter_selection.setModel(self.splitter_model)
        self.splitter_selection.setModelColumn(1)
        self.splitter_selection.setPlaceholderText("Select splitter feature ...")
        
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

        subduct_rift_button = QPushButton("Subduct/Rift")
        subduct_rift_button.clicked.connect(self.do_action)

        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(start_date_label, 0)
        start_time_layout.addWidget(self.start_time, 1)
        
        end_time_layout = QHBoxLayout()
        end_time_layout.addWidget(end_date_label, 0)
        end_time_layout.addWidget(self.end_time, 1)

        plate_filter_layout = QHBoxLayout()
        plate_filter_layout.addWidget(plate_id_label, 0)
        plate_filter_layout.addWidget(self.plate_filter, 1)

        new_plate_id_layout = QHBoxLayout()
        new_plate_id_layout.addWidget(new_plate_id_label, 0)
        new_plate_id_layout.addWidget(self.new_plate_id, 1)

        side_layout = QVBoxLayout()
        side_layout.addLayout(start_time_layout)
        side_layout.addLayout(end_time_layout)
        side_layout.addLayout(plate_filter_layout)
        side_layout.addWidget(QWidget(), 1)
        side_layout.addWidget(self.splitter_selection)
        side_layout.addLayout(new_plate_id_layout)
        side_layout.addWidget(QWidget(), 1)
        side_layout.addWidget(set_feature_save_location_button, 0)
        side_layout.addWidget(set_rotation_save_location_button, 0)
        side_layout.addWidget(subduct_rift_button, 0)
        
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
    def update_start_time(self):
        time = float(self.start_time.text())
        self.feature_model.setStartTimeFilter(time)
        self.splitter_model.setStartTimeFilter(time)
        
    @Slot()
    def update_end_time(self):
        time = float(self.end_time.text())
        self.feature_model.setEndTimeFilter(time)
        self.splitter_model.setEndTimeFilter(time)
    
    @Slot()
    def update_plate_filter(self):
        filter_text = self.plate_filter.text()
        if filter_text == "":
            self.feature_model.setPlateIdFilter([])
        self.feature_model.setPlateIdFilter([id for id in filter_text.split(",") if len(id) > 0])

    @Slot()
    def do_action(self):
        if self.splitter_selection.currentIndex() < 0:
            QMessageBox.critical(self, "Error", "No rift/subduction zone selected!")
            return
        
        splitter_idx = self.splitter_model.index(self.splitter_selection.currentIndex(), 7)
        all_features = [f for lfc in self.session.loaded_feature_collections for f in lfc.feature_collection]
        selected_splitter = next(filter(lambda f: f.get_feature_id().get_string() == self.splitter_model.itemData(splitter_idx)[0], all_features))

        
        if self.start_time.text() == "":
            QMessageBox.critical(self, "Error", "No start time set!")
            return
          
        start_time = float(self.start_time.text())
        
        if self.end_time.text() == "":
            QMessageBox.critical(self, "Error", "No end time set!")
            return
          
        end_time = float(self.end_time.text())
          
        selected_feature_ids = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 7]
        selected_feature_collections = [i.data() for i in self.new_feature_view.selectedIndexes() if i.column() == 8]
        
        selected_features = []

        if selected_splitter.get_feature_type().get_name() != 'MidOceanRidge':
          for i in range(len(selected_feature_ids)):
              fc = next(filter(lambda x: x.shortname == selected_feature_collections[i], self.session.loaded_feature_collections)).feature_collection
              feature = fc.get(lambda f: f.get_feature_id().get_string() == selected_feature_ids[i])
              selected_features.append(feature)
          
          if len(selected_features) == 0:
              QMessageBox.critical(self, "Error", "No features selected!")
              return
        
        if not self.session._rotationModel:
            QMessageBox.critical(self, "Error", "No rotation model selected!")
            return
          
        if not self._feature_save_location:
            self._feature_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
            if not self._feature_save_location:
              QMessageBox.critical(self, "Error", "No feature save location set!")
              return
          
        # if not self._rotation_save_location:
        #     self._rotation_save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "PLATES4 Rotation File (*.rot)")
        #     if not self._rotation_save_location:
        #       QMessageBox.critical(self, "Error", "No rotation save location set!")
        #       return
        
        rc = None
        if selected_splitter.get_feature_type() == FeatureType.gpml_subduction_zone:
          fc = subduct(selected_features, selected_splitter, self.session._rotationFeatureCollection, start_time, end_time)
        elif selected_splitter.get_feature_type() == FeatureType.gpml_continental_rift:
          fc, rc = rift(selected_features, selected_splitter, self.session._rotationFeatureCollection, start_time, end_time)
        elif selected_splitter.get_feature_type() == FeatureType.gpml_mid_ocean_ridge:
          fc = diverge(selected_splitter, self.session._rotationFeatureCollection, start_time, end_time)

          
        # if path.exists(self._feature_save_location):
        #   fc2 = FeatureCollection(self._feature_save_location)
        #   for f in fc:
        #     fc2.add(f)
        #   fc = fc2
        fc.write(self._feature_save_location)

        if rc:
          # if path.exists(self._rotation_save_location):
          #   rc2 = FeatureCollection(self._rotation_save_location)
          #   for f in fc:
          #     rc2.add(f)
          #   rc = rc2
          rc.write(self._rotation_save_location)
        
        QMessageBox.information(self, "Success", "Successfully saved rotation file: " + path.realpath(self._rotation_save_location) + " and feature file: " + path.realpath(self._feature_save_location))
