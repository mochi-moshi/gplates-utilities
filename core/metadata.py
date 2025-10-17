from pygplates.pygplates import PointOnSphere


class MetaPoint:
    def __init__(self, point: PointOnSphere, is_inside: bool) -> None:
        self.point = point
        self.is_inside = is_inside
