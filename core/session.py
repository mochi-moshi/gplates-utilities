import os
from typing import Sequence

from PyQt5.QtCore import QStringListModel, QModelIndex, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget
import pygplates
from dataclasses import dataclass

class LoadedFeatureCollection():
    def __init__(self, path, feature_collection) -> None:
        self.path = path
        self.feature_collection = feature_collection
        self.shortname = os.path.basename(path)

@dataclass
class FeatureData:
  feature_name: str
  feature_name_and_id: str
  feature_type: str
  geometry_type: str
  plate_id: str
  start_time: float
  end_time: float
  feature_id: str
  feature_collection: str
  reconstruction_method: str
  left_plate: str
  right_plate: str

class FeatureDataColumn:
  feature_name = 0
  feature_name_and_id = 1
  feature_type = 2
  geometry_type = 3
  plate_id = 4
  start_time = 5
  end_time = 6
  feature_id = 7
  feature_collection = 8
  reconstruction_method = 9
  left_plate = 10
  right_plate = 11

def extractFeatureDataFromRow(model: QStandardItemModel, row_num: int):
  return FeatureData(
    model.item(row_num, 0).text(),
    model.item(row_num, 1).text(),
    model.item(row_num, 2).text(),
    model.item(row_num, 3).text(),
    model.item(row_num, 4).text(),
    float(model.item(row_num, 5).text()),
    float(model.item(row_num, 6).text()),
    model.item(row_num, 7).text(),
    model.item(row_num, 8).text(),
    model.item(row_num, 9).text(),
    model.item(row_num, 10).text(),
    model.item(row_num, 11).text()
  )
  
def extractFeatureDataFromIndices(indices: list[QModelIndex]):
  return FeatureData(
    [i for i in indices if i.column() == 0][0],
    [i for i in indices if i.column() == 1][0],
    [i for i in indices if i.column() == 2][0],
    [i for i in indices if i.column() == 3][0],
    [i for i in indices if i.column() == 4][0],
    float([i for i in indices if i.column() == 5][0]),
    float([i for i in indices if i.column() == 6][0]),
    [i for i in indices if i.column() == 7][0],
    [i for i in indices if i.column() == 8][0],
    [i for i in indices if i.column() == 9][0],
    [i for i in indices if i.column() == 10][0],
    [i for i in indices if i.column() == 11][0]
  )

def create_feature_item(lfc: LoadedFeatureCollection, feature: pygplates.Feature):
  feature_item: Sequence[QStandardItem] = []

  feature_item.append(QStandardItem(feature.get_name()))                          # Feature Name
  feature_item.append(QStandardItem(f'{feature.get_name()} ({feature.get_feature_id().get_string()})'))      
  feature_item.append(QStandardItem(feature.get_feature_type().get_name()))       # Feature Type
  feature_item.append(QStandardItem(type(feature.get_geometry()).__name__))       # Geometry Type
  feature_item.append(QStandardItem(str(feature.get_reconstruction_plate_id())))  # Plate ID
  feature_item.append(QStandardItem(str(feature.get_valid_time()[0])))            # Start Time
  feature_item.append(QStandardItem(str(feature.get_valid_time()[1])))            # End Time
  feature_item.append(QStandardItem(feature.get_feature_id().get_string()))       # Feature ID
  feature_item.append(QStandardItem(lfc.shortname))                               # Feature Collection (shortname)
  feature_item.append(QStandardItem(feature.get_reconstruction_method()))         # Feature Method
  feature_item.append(QStandardItem(str(feature.get_left_plate())))               # Left Plate
  feature_item.append(QStandardItem(str(feature.get_right_plate())))              # Right Plate
  return feature_item
  
class Session:
    def __init__(self) -> None:
        self.loaded_feature_collections: list[LoadedFeatureCollection] = []
        self.windows: list[QWidget] = []

        self._feature_collection_names = QStringListModel()
        self._feature_model = QStandardItemModel()
        self._feature_model.setColumnCount(12)
        self._feature_model.setHorizontalHeaderLabels(["Feature Name", "Feature Name (ID)", "Feature Type", "Geometry Type", "Plate ID", "Start Time", "End Time", "Feature ID", "Feature Collection", "Reconstruction Method", "Left Plate", "Right Plate"])

        self._rotationModel_path: str = ""
        self._rotationModel: pygplates.RotationModel = None
        self._rotationFeatureCollection: pygplates.FeatureCollection = None

        self._project_file: str = ""
        self._project_path: str = ""
        # TODO: Think about caring about dirty state
        # self._project_dirty: bool = False
    
    def reset_project(self) -> None:
        self._project_file = ""
        self.loaded_feature_collections.clear()
        self._rotationModel_path = ""
        self._rotationModel = None

        self._feature_collection_names.setStringList([])
        self.reload_features()

    def set_project(self, project_file_path: str) -> None:
        self._project_file = project_file_path
        self._project_path = os.path.dirname(project_file_path)

    def load_rotation_model(self, path):
        self._rotationModel_path = path
        self._rotationModel = pygplates.RotationModel(path)
        self._rotationFeatureCollection = pygplates.FeatureCollection(path)
    
    def soft_reload_rotation_model(self):
        if self._rotationModel_path == "":
            #QMessageBox.warning(None, "Error", "Cannot reload uninitialized feature model.")
            return
        
        self._rotationModel = pygplates.RotationModel(self._rotationFeatureCollection)
        
    
    def reload_rotation_model(self):
        if self._rotationModel_path == "":
            #QMessageBox.warning(None, "Error", "Cannot reload uninitialized feature model.")
            return
        
        self._rotationModel = pygplates.RotationModel(self._rotationModel_path)
        self._rotationFeatureCollection = pygplates.FeatureCollection(self._rotationModel_path)

    
    def get_feature_collection_model(self):
        return self._feature_collection_names
    
    def get_feature_model(self):
        return self._feature_model
    
    def load_feature_collections(self, paths: list[str]) -> None:
        new_paths = [p for p in paths if len([lfc for lfc in self.loaded_feature_collections if lfc.path == p]) == 0]

        if len(new_paths) == 0:
            return
        
        for path in new_paths:
            lfc = LoadedFeatureCollection(path, pygplates.FeatureCollection(path))
            self.loaded_feature_collections.append(lfc)
            for feature in lfc.feature_collection:
                self._feature_model.appendRow(create_feature_item(lfc, feature))

        # Completely update our names model
        self._feature_collection_names.setStringList([x.shortname for x in self.loaded_feature_collections])
    
    def unload_feature_collection(self, shortname):
        lfc = next(filter(lambda x: x.shortname == shortname, self.loaded_feature_collections), None)

        if not lfc:
            return
        
        self.loaded_feature_collections.remove(lfc)

        # Update Feature Collection name model
        index = self._feature_collection_names.stringList().index(shortname)
        self._feature_collection_names.removeRow(index)

        # Update Feature Model
        items = self._feature_model.findItems(shortname, Qt.MatchFlag.MatchFixedString, FeatureDataColumn.feature_collection)
        for i in items:
            self._feature_model.removeRow(i.row())
    
    def reload_features(self):
        self._feature_model.removeRows(0, self._feature_model.rowCount())
        self._feature_model.setColumnCount(12)
        self._feature_model.setHorizontalHeaderLabels(["Feature Name", "Feature Name (ID)", "Feature Type", "Geometry Type", "Plate ID", "Start Time", "End Time", "Feature ID", "Feature Collection", "Reconstruction Method", "Left Plate", "Right Plate"])

        for lfc in self.loaded_feature_collections:
            lfc.feature_collection = pygplates.FeatureCollection(lfc.path)

            for feature in lfc.feature_collection:
                self._feature_model.appendRow(create_feature_item(lfc, feature))