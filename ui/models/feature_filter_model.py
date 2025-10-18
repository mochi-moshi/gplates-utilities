from PyQt5.QtCore import QSortFilterProxyModel
from core.session import extractFeatureDataFromRow


class FeatureFilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._start_time_filter: float = None
        self._end_time_filter: float = None
        self._id_filter: list[str] = []
        self._name_filter: list[str] = []
        self._geometry_filter: list[str] = []
        self._reconstruction_filter: list[str] = []
        self._collection_filter: list[str] = []
        self._type_filter: list[str] = []
        self._excluded_features: list[str] = []

    def filterAcceptsRow(self, row_num: int, _) -> bool:
        model = self.sourceModel()
        data = extractFeatureDataFromRow(model, row_num)

        valid_time = (
            self._start_time_filter is None
            or data.end_time < self._start_time_filter <= data.start_time
        ) and (self._end_time_filter is None or self._end_time_filter < data.start_time)
        valid_id = len(self._id_filter) == 0 or (
            data.reconstruction_method == "ByPlateId"
            and data.plate_id in self._id_filter
            or data.reconstruction_method
            in [
                "HalfStageRotation",
                "HalfStageRotationVersion2",
                "HalfStageRotationVersion3",
            ]
            and (
                data.left_plate in self._id_filter
                or data.right_plate in self._id_filter
            )
        )
        valid_name = len(self._name_filter) == 0 or any(
            name in data.feature_name_and_id for name in self._name_filter
        )
        valid_geometry = len(self._geometry_filter) == 0 or any(
            geom == data.geometry_type for geom in self._geometry_filter
        )
        valid_reconstruction = len(self._reconstruction_filter) == 0 or any(
            recon == data.reconstruction_method for recon in self._reconstruction_filter
        )
        valid_collection = len(self._collection_filter) == 0 or any(
            collection == data.feature_collection
            for collection in self._collection_filter
        )
        valid_type = len(self._type_filter) == 0 or any(
            typ == data.feature_type for typ in self._type_filter
        )
        excluded = data.feature_id in self._excluded_features

        return not excluded and (
            valid_time
            and valid_id
            and valid_name
            and valid_geometry
            and valid_reconstruction
            and valid_collection
            and valid_type
        )

    def setStartTimeFilter(self, time: float):
        # self.beginFilterChange()
        self._start_time_filter = time
        self.invalidateFilter()

    def setEndTimeFilter(self, time: float):
        # self.beginFilterChange()
        self._end_time_filter = time
        self.invalidateFilter()

    def setTimeRangeFilter(self, start: float, end: float):
        # self.beginFilterChange()
        self._start_time_filter = start
        self._end_time_filter = end
        self.invalidateFilter()

    def setPlateIdFilter(self, ids: list[str]):
        # self.beginFilterChange()
        self._id_filter = ids or []
        self.invalidateFilter()

    def setNameFilter(self, names: list[str]):
        # self.beginFilterChange()
        self._name_filter = names or []
        self.invalidateFilter()

    def setGeometryFilter(self, geometries: list[str]):
        # self.beginFilterChange()
        self._geometry_filter = geometries or []
        self.invalidateFilter()

    def setReconstructionFilter(self, reconstruction_methods: list[str]):
        # self.beginFilterChange()
        self._reconstruction_filter = reconstruction_methods or []
        self.invalidateFilter()

    def setCollectionFilter(self, collections: list[str]):
        # self.beginFilterChange()
        self._collection_filter = collections or []
        self.invalidateFilter()

    def setTypeFilter(self, types: list[str]):
        # self.beginFilterChange()
        self._type_filter = types or []
        self.invalidateFilter()

    def setFeatureIdFilter(self, ids: list[str]):
        # self.beginFilterChange()
        self._excluded_features = ids or []
        self.invalidateFilter()
