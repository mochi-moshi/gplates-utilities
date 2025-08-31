from PySide6.QtCore import QSortFilterProxyModel
from core.session import extractFeatureDataFromRow


def is_valid(start: float, end: float, trange: tuple[float, float]):
  return start >= trange[0] >= end and start >= trange[1]

class TimeRangeFilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._start_time_filter: float = float("inf")
        self._end_time_filter: float = float("-inf")
        self._accepted_ids: list[str] = []
    
    def filterAcceptsRow(self, row_num: int, _) -> bool:
        model = self.sourceModel()
        data = extractFeatureDataFromRow(model, row_num)
        
        start_time = float(model.item(row_num, 5).text())
        end_time = float(model.item(row_num, 6).text())

        return (len(self._accepted_ids) == 0 or (data.reconstruction_method == 'ByPlateId' and data.plate_id in self._accepted_ids or data.reconstruction_method in ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3'] and (data.left_plate in self._accepted_ids or data.right_plate in self._accepted_ids))) and is_valid(self._start_time_filter, self._end_time_filter, (start_time, end_time))
    
    def setStartTimeFilter(self, time: float):
        self.beginFilterChange()
        self._start_time_filter = time
        self.invalidateFilter()
        
    def setEndTimeFilter(self, time: float):
        self.beginFilterChange()
        self._end_time_filter = time
        self.invalidateFilter()
        
    def setTimeRangeFilter(self, start: float, end: float):
        self.beginFilterChange()
        self._start_time_filter = start
        self._end_time_filter = end
        self.invalidateFilter()
    
    def setPlateIdFilter(self, ids: list[str]):
        self.beginFilterChange()
        self._accepted_ids = ids
        self.invalidateFilter()