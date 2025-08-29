from typing import List
from PySide6.QtCore import QSortFilterProxyModel


class LineFilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._time_filter: float = float("inf")
        self._start_time_filter: float = None
        self._end_time_filter: float = None
        self._accepted_ids: List[str] = []
        self._accepted_types: List[str] = []
    
    def filterAcceptsRow(self, row_num: int, _) -> bool:
        # Get the underlying model
        model: QStandardItemModel = self.sourceModel()  # type: ignore | We know what data we are dealing with
        
        geo_type = model.item(row_num, 3).text()
        plateId = model.item(row_num, 4).text()
        start_time = float(model.item(row_num, 5).text())
        end_time = float(model.item(row_num, 6).text())
        feature_type = model.item(row_num, 2).text()
        
        return (
            geo_type == "PolylineOnSphere" and
            (self._time_filter is None or start_time >= self._time_filter >= end_time) and
            (self._start_time_filter is None or  self._start_time_filter >= start_time and self._start_time_filter >= end_time) and
            (self._end_time_filter is None or  start_time >= self._end_time_filter) and
            (len(self._accepted_ids) == 0 or plateId in self._accepted_ids) and
            (len(self._accepted_types) == 0 or feature_type in self._accepted_types)
        )
    
    def setTimeFilter(self, time: float):
        self.beginFilterChange()
        self._time_filter = time
        self._start_time_filter = None
        self._end_time_filter = None
        self.invalidateFilter()
        
    def setStartTimeFilter(self, time: float):
        self.beginFilterChange()
        self._start_time_filter = time
        self._time_filter = None
        self.invalidateFilter()
        
    def setEndTimeFilter(self, time: float):
        self.beginFilterChange()
        self._end_time_filter = time
        self._time_filter = None
        self.invalidateFilter()
    
    def setPlateIdFilter(self, ids: List[str]):
        self.beginFilterChange()
        self._accepted_ids = ids
        self.invalidateFilter()
    
    def setFeatureTypeFilter(self, types: List[str]):
        self.beginFilterChange()
        self._accepted_types = types
        self.invalidateFilter()
