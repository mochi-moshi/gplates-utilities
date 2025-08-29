from pygplates import Feature, FeatureCollection, FeatureType, PolygonOnSphere, PolylineOnSphere, ReconstructSnapshot, reverse_reconstruct, RotationModel

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
    
    disjointA = [PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(outsideB + insideA)]
    disjointB = [PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(outsideA + insideB)]
    return disjointA + disjointB
difference_of_polygons = a_xor_b

def union_of_polygons(polyA: PolygonOnSphere, polyB: PolygonOnSphere) -> list[PolygonOnSphere]:
    outside = []
    overlapA = polyA.partition(polyB, partitioned_geometries_outside=outside)
    overlapB = polyB.partition(polyA, partitioned_geometries_outside=outside)

    if overlapA == PolygonOnSphere.PartitionResult.outside and overlapB == PolygonOnSphere.PartitionResult.outside:
        return [polyA, polyB]

    return [PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(outside)]
  
def a_not_b(polyA: PolygonOnSphere, polyB: PolygonOnSphere) -> list[PolygonOnSphere]:
    lines = []
    polyA.partition(polyB, partitioned_geometries_inside=lines)
    polyB.partition(polyA, partitioned_geometries_outside=lines)
    
    return [PolygonOnSphere(g[:]) for g in PolylineOnSphere.join(lines)]

def join_plate_features_by_intersect(plates: list[Feature], rotation_model: RotationModel, split_time: float, *, feature_type: FeatureType = FeatureType.gpml_unclassified_feature, reconstruction_plate_id: int | None = None) -> FeatureCollection:
    initial_feature_collection = FeatureCollection(plates)
    snapshot = ReconstructSnapshot(initial_feature_collection, rotation_model, split_time)
    snapshot_features = snapshot.get_reconstructed_geometries()

    new_collection = FeatureCollection()

    current_geometry = [snapshot_features[0].get_reconstructed_geometry()]
    name_union = plates[0].get_name()
    for i, geometry in enumerate(snapshot_features[1:], 1):
        name_union += ' ' + plates[i].get_name()
          
        feature_geometry = geometry.get_reconstructed_geometry()
          
        new_geometry = []
        for geom in current_geometry:
            new_geometry += intersection_of_polygons(geom, feature_geometry)
        current_geometry = new_geometry
        if len(current_geometry) == 0:
            break

    if len(current_geometry) != 0:
        reconstruction_ids = set([p.get_reconstruction_plate_id() for p in plates]) if reconstruction_plate_id is None else [reconstruction_plate_id]
        for reconstruction_id in reconstruction_ids:
            for i, geometry in enumerate(current_geometry):
                new_plate = Feature.create_reconstructable_feature(
                    feature_type, geometry, f"Intersect {name_union} [{i}]{reconstruction_id if reconstruction_plate_id is None else ''}",
                    reconstruction_plate_id=reconstruction_id,
                    valid_time=(split_time, float("-inf"))
                )
                new_collection.add(new_plate)
    
    reverse_reconstruct(new_collection, rotation_model, split_time)

    return new_collection
  
def join_plate_features_by_union(plates: list[Feature], rotation_model: RotationModel, split_time: float, *, feature_type: FeatureType = FeatureType.gpml_unclassified_feature, reconstruction_plate_id: int | None = None) -> FeatureCollection:
    initial_feature_collection = FeatureCollection(plates)
    snapshot = ReconstructSnapshot(initial_feature_collection, rotation_model, split_time)
    snapshot_features = snapshot.get_reconstructed_geometries()

    new_collection = FeatureCollection()

    current_geometry = [snapshot_features[0].get_reconstructed_geometry()]
    name_union = plates[0].get_name()
    for i, geometry in enumerate(snapshot_features[1:], 1):
        name_union += ' ' + plates[i].get_name()
          
        feature_geometry = geometry.get_reconstructed_geometry()
          
        new_geometry = []
        for geom in current_geometry:
            new_geometry += union_of_polygons(geom, feature_geometry)
        current_geometry = new_geometry
        if len(current_geometry) == 0:
            break

    if len(current_geometry) != 0:
        reconstruction_ids = set([p.get_reconstruction_plate_id() for p in plates]) if reconstruction_plate_id is None else [reconstruction_plate_id]
        for reconstruction_id in reconstruction_ids:
            for i, geometry in enumerate(current_geometry):
                new_plate = Feature.create_reconstructable_feature(
                    feature_type, geometry, f"Union {name_union} [{i}]{reconstruction_id if reconstruction_plate_id is None else ''}",
                    reconstruction_plate_id=reconstruction_id,
                    valid_time=(split_time, float("-inf"))
                )
                new_collection.add(new_plate)
    
    reverse_reconstruct(new_collection, rotation_model, split_time)

    return new_collection
  
def split_plate_features_by_difference(plates: list[Feature], rotation_model: RotationModel, split_time: float, *, feature_type: FeatureType = FeatureType.gpml_unclassified_feature, reconstruction_plate_id: int | None = None) -> FeatureCollection:
    initial_feature_collection = FeatureCollection(plates)
    snapshot = ReconstructSnapshot(initial_feature_collection, rotation_model, split_time)
    snapshot_features = snapshot.get_reconstructed_geometries()

    new_collection = FeatureCollection()

    current_geometry = [snapshot_features[0].get_reconstructed_geometry()]
    name_union = plates[0].get_name()
    for i, geometry in enumerate(snapshot_features[1:], 1):
        name_union += ' ' + plates[i].get_name()
          
        feature_geometry = geometry.get_reconstructed_geometry()
          
        new_geometry = []
        for geom in current_geometry:
            new_geometry += difference_of_polygons(geom, feature_geometry)
        current_geometry = new_geometry
        if len(current_geometry) == 0:
            break

    if len(current_geometry) != 0:
        reconstruction_ids = set([p.get_reconstruction_plate_id() for p in plates]) if reconstruction_plate_id is None else [reconstruction_plate_id]
        for reconstruction_id in reconstruction_ids:
            for i, geometry in enumerate(current_geometry):
                new_plate = Feature.create_reconstructable_feature(
                    feature_type, geometry, f"Difference {name_union} [{i}]{reconstruction_id if reconstruction_plate_id is None else ''}",
                    reconstruction_plate_id=reconstruction_id,
                    valid_time=(split_time, float("-inf"))
                )
                new_collection.add(new_plate)
    
    reverse_reconstruct(new_collection, rotation_model, split_time)

    return new_collection