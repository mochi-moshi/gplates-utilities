from pygplates import (
    Feature,
    FeatureCollection,
    FeatureType,
    PolygonOnSphere,
    PolylineOnSphere,
    ReconstructSnapshot,
    reverse_reconstruct,
    RotationModel,
    GreatCircleArc,
    PointOnSphere,
)
import itertools


def a_and_b(polyA: PolygonOnSphere, polyB: PolygonOnSphere) -> list[PolygonOnSphere]:
    inside = []
    polyA.partition(polyB, partitioned_geometries_inside=inside)
    polyB.partition(polyA, partitioned_geometries_inside=inside)

    return [PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(inside)]


intersection_of_polygons = a_and_b


def a_xor_b(polyA: PolygonOnSphere, polyB: PolygonOnSphere) -> list[PolygonOnSphere]:
    insideA, outsideA, insideB, outsideB = [], [], [], []
    polyA.partition(polyB, insideA, outsideA)
    polyB.partition(polyA, insideB, outsideB)

    disjointA = [
        PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(outsideB + insideA)
    ]
    disjointB = [
        PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(outsideA + insideB)
    ]
    return disjointA + disjointB


difference_of_polygons = a_xor_b


def same_and_direction(a: GreatCircleArc, b: GreatCircleArc) -> int:
    if (
        PointOnSphere.distance(a.get_start_point(), b.get_start_point()) < 0.05
        and PointOnSphere.distance(a.get_end_point(), b.get_end_point()) < 0.05
    ):
        return 1
    if (
        PointOnSphere.distance(a.get_start_point(), b.get_end_point()) < 0.05
        and PointOnSphere.distance(a.get_end_point(), b.get_start_point()) < 0.05
    ):
        return -1
    return 0


def distances(a, b):
    return (
        PointOnSphere.distance(a.get_start_point(), b.get_start_point()),
        PointOnSphere.distance(a.get_end_point(), b.get_end_point()),
        PointOnSphere.distance(a.get_start_point(), b.get_end_point()),
        PointOnSphere.distance(a.get_end_point(), b.get_start_point()),
    )


def arc_to_polyline(arc: GreatCircleArc, reverse: bool = False):
    if reverse:
        return PolylineOnSphere([arc.get_end_point(), arc.get_start_point()])
    return PolylineOnSphere([arc.get_start_point(), arc.get_end_point()])


def arc_to_points(arc: GreatCircleArc, reverse: bool = False):
    if reverse:
        return [arc.get_end_point(), arc.get_start_point()]
    return [arc.get_start_point(), arc.get_end_point()]


def union_of_polygons(
    polyA: PolygonOnSphere, polyB: PolygonOnSphere
) -> list[PolygonOnSphere]:
    if not polyA and not polyB:
        return []
    if not polyA:
        return [polyB]
    if not polyB:
        return [polyA]
    outside = []
    inside = []
    overlapA = polyA.partition(polyB, inside, partitioned_geometries_outside=outside)
    overlapB = polyB.partition(polyA, inside, partitioned_geometries_outside=outside)

    if (
        overlapA == PolygonOnSphere.PartitionResult.outside
        and overlapB == PolygonOnSphere.PartitionResult.outside
    ):
        return [polyA, polyB]

    return [PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(outside)]


def a_not_b(polyA: PolygonOnSphere, polyB: PolygonOnSphere) -> list[PolygonOnSphere]:
    lines = []
    polyA.partition(polyB, partitioned_geometries_inside=lines)
    polyB.partition(polyA, partitioned_geometries_outside=lines)

    return [PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(lines)]


def join_plate_features_by_intersect(
    plates: list[Feature],
    rotation_model: RotationModel,
    split_time: float,
    *,
    feature_type: FeatureType = FeatureType.gpml_unclassified_feature,
    reconstruction_plate_id: int | None = None,
) -> FeatureCollection:
    snapshot = ReconstructSnapshot(plates, rotation_model, split_time)
    snapshot_features = snapshot.get_reconstructed_geometries(
        same_order_as_reconstructable_features=True
    )

    new_collection = FeatureCollection()

    current_geometry = [snapshot_features[0].get_reconstructed_geometry()]
    name_union = plates[0].get_name()
    for i, geometry in enumerate(snapshot_features[1:], 1):
        name_union += " " + plates[i].get_name()

        feature_geometry = geometry.get_reconstructed_geometry()

        new_geometry = []
        for geom in current_geometry:
            new_geometry += intersection_of_polygons(geom, feature_geometry)
        current_geometry = new_geometry
        if len(current_geometry) == 0:
            break

    if len(current_geometry) != 0:
        reconstruction_ids = (
            set([p.get_reconstruction_plate_id() for p in plates])
            if reconstruction_plate_id is None
            else [reconstruction_plate_id]
        )
        for reconstruction_id in reconstruction_ids:
            for i, geometry in enumerate(current_geometry):
                new_plate = Feature.create_reconstructable_feature(
                    feature_type,
                    geometry,
                    f"Intersect {name_union} [{i}]{reconstruction_id if reconstruction_plate_id is None else ''}",
                    reconstruction_plate_id=reconstruction_id,
                    valid_time=(split_time, float("-inf")),
                )
                new_collection.add(new_plate)

    reverse_reconstruct(new_collection, rotation_model, split_time)

    return new_collection


def join_plate_features_by_union(
    plates: list[Feature],
    rotation_model: RotationModel,
    split_time: float,
    *,
    feature_type: FeatureType = FeatureType.gpml_unclassified_feature,
    reconstruction_plate_id: int | None = None,
) -> FeatureCollection:
    snapshot = ReconstructSnapshot(plates, rotation_model, split_time)
    snapshot_features = snapshot.get_reconstructed_geometries(
        same_order_as_reconstructable_features=True
    )

    new_collection = FeatureCollection()

    current_geometry = [snapshot_features[0].get_reconstructed_geometry()]
    name_union = plates[0].get_name()
    for i, geometry in enumerate(snapshot_features[1:], 1):
        name_union += " " + plates[i].get_name()

        feature_geometry = geometry.get_reconstructed_geometry()

        new_geometry = []
        for geom in current_geometry:
            new_geometry += union_of_polygons(geom, feature_geometry)
        current_geometry = new_geometry
        if len(current_geometry) == 0:
            break

    if len(current_geometry) != 0:
        reconstruction_ids = (
            set([p.get_reconstruction_plate_id() for p in plates])
            if reconstruction_plate_id is None
            else [reconstruction_plate_id]
        )
        for reconstruction_id in reconstruction_ids:
            for i, geometry in enumerate(current_geometry):
                new_plate = Feature.create_reconstructable_feature(
                    feature_type,
                    geometry,
                    f"Union {name_union} [{i}]{reconstruction_id if reconstruction_plate_id is None else ''}",
                    reconstruction_plate_id=reconstruction_id,
                    valid_time=(split_time, float("-inf")),
                )
                new_collection.add(new_plate)

    reverse_reconstruct(new_collection, rotation_model, split_time)

    return new_collection


def split_plate_features_by_difference(
    plates: list[Feature],
    rotation_model: RotationModel,
    split_time: float,
    *,
    feature_type: FeatureType = FeatureType.gpml_unclassified_feature,
    reconstruction_plate_id: int | None = None,
) -> FeatureCollection:
    snapshot = ReconstructSnapshot(plates, rotation_model, split_time)
    snapshot_features = snapshot.get_reconstructed_geometries(
        same_order_as_reconstructable_features=True
    )

    new_collection = FeatureCollection()

    current_geometry = [snapshot_features[0].get_reconstructed_geometry()]
    name_union = plates[0].get_name()
    for i, geometry in enumerate(snapshot_features[1:], 1):
        name_union += " " + plates[i].get_name()

        feature_geometry = geometry.get_reconstructed_geometry()

        new_geometry = []
        for geom in current_geometry:
            new_geometry += difference_of_polygons(geom, feature_geometry)
        current_geometry = new_geometry
        if len(current_geometry) == 0:
            break

    if len(current_geometry) != 0:
        reconstruction_ids = (
            set([p.get_reconstruction_plate_id() for p in plates])
            if reconstruction_plate_id is None
            else [reconstruction_plate_id]
        )
        for reconstruction_id in reconstruction_ids:
            for i, geometry in enumerate(current_geometry):
                new_plate = Feature.create_reconstructable_feature(
                    feature_type,
                    geometry,
                    f"Difference {name_union} [{i}]{reconstruction_id if reconstruction_plate_id is None else ''}",
                    reconstruction_plate_id=reconstruction_id,
                    valid_time=(split_time, float("-inf")),
                )
                new_collection.add(new_plate)

    reverse_reconstruct(new_collection, rotation_model, split_time)

    return new_collection
