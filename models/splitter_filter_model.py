from typing import List
from PySide6.QtCore import QSortFilterProxyModel


class SplitterFilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._time_filter: float = float("inf")
        self._accepted_ids: List[str] = []
        self._excluded_ids: List[str] = []
        self._accepted_types: List[str] = []
    
    def filterAcceptsRow(self, row_num: int, _) -> bool:
        # Get the underlying model
        model: QStandardItemModel = self.sourceModel()  # type: ignore | We know what data we are dealing with
        
        geo_type = model.item(row_num, 2).text()
        plateId = model.item(row_num, 3).text()
        start_time = float(model.item(row_num, 4).text())
        end_time = float(model.item(row_num, 5).text())
        feature_id = model.item(row_num, 6).text()
        feature_type = model.item(row_num, 1).text()
        
        return (
            (geo_type == "PolylineOnSphere" or geo_type == "PolygonOnSphere" ) and
            (start_time >= self._time_filter >= end_time) and
            (len(self._accepted_ids) == 0 or plateId in self._accepted_ids) and
            (len(self._excluded_ids) == 0 or feature_id not in self._excluded_ids) and
            (len(self._accepted_types) == 0 or feature_type in self._accepted_types)
        )
    
    def setTimeFilter(self, time: float):
        self.beginFilterChange()
        self._time_filter = time
        self.invalidateFilter()
    
    def setPlateIdFilter(self, ids: List[str]):
        self.beginFilterChange()
        self._accepted_ids = ids
        self.invalidateFilter()
        
    def setFeatureIdFilter(self, ids: List[str]):
        self.beginFilterChange()
        self._excluded_ids = ids
        self.invalidateFilter()
    
    def setFeatureTypeFilter(self, types: List[str]):
        self.beginFilterChange()
        self._accepted_types = types
        self.invalidateFilter()
