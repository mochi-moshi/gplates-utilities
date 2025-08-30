from typing import List
from PySide6.QtCore import QSortFilterProxyModel
from core.session import extractFeatureDataFromRow


class SplitterFilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._time_filter: float = float("inf")
        self._accepted_ids: List[str] = []
        self._excluded_ids: List[str] = []
        self._accepted_types: List[str] = []
    
    def filterAcceptsRow(self, row_num: int, _) -> bool:
        model = self.sourceModel()
        data = extractFeatureDataFromRow(model, row_num)
        
        return (
            (data.geometry_type == "PolylineOnSphere" or data.geometry_type == "PolygonOnSphere" ) and
            (data.start_time >= self._time_filter >= data.end_time) and
            (len(self._accepted_ids) == 0 or data.plate_id in self._accepted_ids) and
            (len(self._excluded_ids) == 0 or data.feature_id not in self._excluded_ids) and
            (len(self._accepted_types) == 0 or data.feature_type in self._accepted_types)
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
