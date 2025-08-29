from os import path
from PySide6.QtCore import Slot
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from core.line_splitter import split_line_features
from core.session import Session
from models.line_filter_model import LineFilterModel
from ui.feature_collection_loader import FeatureCollectionLoader

from pygplates import  FeatureCollection

class LineSplitterWindow(QWidget):
    def __init__(self, session: Session):
        super().__init__()

        self._save_location = ""

        self.session = session

        self.line_model = LineFilterModel()
        self.line_model.setSourceModel(session.get_feature_model())

        self.resize(900, 400)

        self.debugwindow = FeatureCollectionLoader(self.session)

        split_date_label = QLabel("Split Time:")
        self.split_date = QLineEdit()
        self.split_date.setValidator(QDoubleValidator())
        self.split_date.editingFinished.connect(self.update_split_time)

        plate_id_label = QLabel("Plate ID(s):")
        self.plate_filter = QLineEdit()
        self.plate_filter.setValidator(QRegularExpressionValidator("\\d+(,\\d*)*"))
        self.plate_filter.editingFinished.connect(self.update_id_filter)

        self.lineA_selection = QComboBox()
        self.lineA_selection.setModel(self.line_model)
        self.lineA_selection.setModelColumn(1)
        self.lineA_selection.setPlaceholderText("Select first line feature ...")

        self.lineB_selection = QComboBox()
        self.lineB_selection.setModel(self.line_model)
        self.lineB_selection.setModelColumn(1)
        self.lineB_selection.setPlaceholderText("Select second line feature ...")
        
        set_save_location_button = QPushButton("Set Save Location")
        set_save_location_button.clicked.connect(self.set_save_location)

        split_button = QPushButton("Split")
        split_button.clicked.connect(self.perform_split)

        split_date_layout = QHBoxLayout()
        split_date_layout.addWidget(split_date_label)
        split_date_layout.addWidget(self.split_date)
        
        plate_id_layout = QHBoxLayout()
        plate_id_layout.addWidget(plate_id_label)
        plate_id_layout.addWidget(self.plate_filter)

        layout = QVBoxLayout()
        layout.addLayout(split_date_layout, 0)
        layout.addLayout(plate_id_layout, 0)
        layout.addSpacing(16)
        layout.addWidget(QLabel("Lines:"), 0)
        layout.addWidget(self.lineA_selection, 0)
        layout.addWidget(self.lineB_selection, 0)
        layout.addWidget(QWidget(), 1)
        layout.addWidget(set_save_location_button, 0)
        layout.addWidget(split_button, 0)

        self.setLayout(layout)
    
    @Slot()
    def update_split_time(self):
        time = float(self.split_date.text())
        self.line_model.setTimeFilter(time)
    
    @Slot()
    def update_id_filter(self):
        filter_text = self.plate_filter.text()
        if filter_text == "":
            self.line_model.setPlateIdFilter([])
        self.line_model.setPlateIdFilter([id for id in filter_text.split(",") if len(id) > 0])
    
    @Slot()
    def set_save_location(self):
        save_location, _ = QFileDialog.getSaveFileName(self, "Set Resulting Feature Collection", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
        if save_location:
            self._save_location = save_location
    
    @Slot()
    def perform_split(self):
        if self.lineA_selection.currentIndex() < 0 or self.lineB_selection.currentIndex() < 0:
            QMessageBox.critical(self, "Error", "Please select 2 lines to split")
            return
        
        all_features = [f for lfc in self.session.loaded_feature_collections for f in lfc.feature_collection]
        line_a_idx = self.line_model.index(self.lineA_selection.currentIndex(), 7)
        line_b_idx = self.line_model.index(self.lineB_selection.currentIndex(), 7)
        line_a = next(filter(lambda f: f.get_feature_id().get_string() == self.line_model.itemData(line_a_idx)[0], all_features))
        line_b = next(filter(lambda f: f.get_feature_id().get_string() == self.line_model.itemData(line_b_idx)[0], all_features))

        if self.split_date.text() == "":
            QMessageBox.critical(self, "Error", "No split time set!")
            return
        
        split_date = float(self.split_date.text())
        
        if not self.session._rotationModel:
            QMessageBox.critical(self, "Error", "No rotation model selected!")
            return
        
        if not self._save_location:
            QMessageBox.critical(self, "Error", "No save location set!")
            return
        
        if not line_a or not line_b:
            QMessageBox.critical(self, "Error", "Please select 2 lines to split")
            return

        fc = split_line_features(line_a, line_b, self.session._rotationModel, split_date)
        
        if path.exists(self._save_location):
          fc2 = FeatureCollection(self._save_location)
          for f in fc:
            fc2.add(f)
          fc = fc2
        fc.write(self._save_location)
        QMessageBox.information(self, "Success", "Successfully saved split lines: " + path.realpath(self._save_location))