from PyQt5.QtCore import QSortFilterProxyModel
from core.session import extractFeatureDataFromRow


class PolygonFilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._time_filter: float = float("inf")
        self._accepted_ids: list[str] = []
    
    def filterAcceptsRow(self, row_num: int, _) -> bool:
        model = self.sourceModel()
        data = extractFeatureDataFromRow(model, row_num)

        return data.geometry_type == "PolygonOnSphere" and (len(self._accepted_ids) == 0 or (data.reconstruction_method == 'ByPlateId' and data.plate_id in self._accepted_ids or data.reconstruction_method in ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3'] and (data.left_plate in self._accepted_ids or data.right_plate in self._accepted_ids))) and (data.start_time >= self._time_filter >= data.end_time)
    
    def setTimeFilter(self, time: float):
        # self.beginFilterChange()
        self._time_filter = time
        self.invalidate()
    
    def setPlateIdFilter(self, ids: list[str]):
        # self.beginFilterChange()
        self._accepted_ids = ids
        self.invalidate()