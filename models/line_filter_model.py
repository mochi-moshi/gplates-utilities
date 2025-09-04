from typing import List
from PySide6.QtCore import QSortFilterProxyModel
from core.session import extractFeatureDataFromRow

class LineFilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._time_filter: float = None
        self._start_time_filter: float = None
        self._end_time_filter: float = None
        self._accepted_ids: List[str] = []
        self._accepted_types: List[str] = []
        self._excluded_features = []
    
    def filterAcceptsRow(self, row_num: int, _) -> bool:
        # Get the underlying model
        model = self.sourceModel()
        data = extractFeatureDataFromRow(model, row_num)

        # print(data, data.geometry_type == "PolylineOnSphere",
        #     (self._time_filter is None or data.start_time >= self._time_filter >= data.end_time),
        #     (self._start_time_filter is None or  self._start_time_filter >= data.start_time and self._start_time_filter >= data.end_time),
        #     (self._end_time_filter is None or  data.start_time >= self._end_time_filter),
        #     (len(self._accepted_ids) == 0 or data.plate_id in self._accepted_ids),
        #     (len(self._accepted_types) == 0 or data.feature_type in self._accepted_types))
        
        return (
            data.geometry_type == "PolylineOnSphere" and
            (self._time_filter is None or data.start_time >= self._time_filter >= data.end_time) and
            (self._start_time_filter is None or  self._start_time_filter <= data.start_time and self._start_time_filter >= data.end_time) and
            (self._end_time_filter is None or  data.start_time >= self._end_time_filter) and
            (len(self._accepted_ids) == 0 or (data.reconstruction_method == 'ByPlateId' and data.plate_id in self._accepted_ids or data.reconstruction_method in ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3'] and (data.left_plate in self._accepted_ids or data.right_plate in self._accepted_ids))) and
            (len(self._accepted_types) == 0 or data.feature_type in self._accepted_types) and
            (len(self._excluded_features) == 0 or data.feature_id not in self._excluded_features)
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
    
    def setFeatureIdFilter(self, ids: List[str]):
        self.beginFilterChange()
        self._excluded_features = ids
        self.invalidateFilter()
