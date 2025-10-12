from pygplates import FeatureCollection, Feature, RotationModel, ReconstructSnapshot, PropertyName, FeatureType, reverse_reconstruct
from pygplates import PointOnSphere, MultiPointOnSphere, PolylineOnSphere, PolygonOnSphere, GreatCircleArc, Vector3D, GeometryOnSphere, GpmlPlateId, Enumeration, EnumerationType, GeoTimeInstant

from ..line_splitter import split_line_by
from ..plate_splitter import split_plate_by_line
from ..rotations import split_rotation_features_by_plate_id


def rift(features: list[Feature], rift: Feature, rotation_features: FeatureCollection, split_time: float, left_plate_id: int, right_plate_id: int, max_transition_size = 10, *, generate_mor: bool = False, use_topologies: bool = False):
  """
  Model continental rifting by splitting features along a rift line.
  
  Args:
    features: List of features to be split by rifting
    rift: The rift line feature defining the rifting boundary
    rotation_model: Rotation model for reconstruction
    split_time: Time at which rifting occurs
    left_plate_id: Plate ID for features on the left side of the rift
    right_plate_id: Plate ID for features on the right side of the rift
    max_transition_size: Maximum size for transition zones (unused in basic implementation)
    generate_mor: Whether to generate a MOR from the rift
    use_topologies: Whether to use topological networks (unused in basic implementation)
    
  Returns:
    FeatureCollection: Collection of split features with new plate IDs
  """
  if not features:
    return FeatureCollection()

  # Validate that all features have the same reconstruction plate id
  plate_ids = [f.get_reconstruction_plate_id() for f in features if f.get_reconstruction_method() == 'ByPlateId']
  if not plate_ids:
    raise ValueError("At least one feature must have a single plate id")
  
  plate_id =  plate_ids[0]
  if not all(f.get_reconstruction_plate_id() == plate_id for f in features if f.get_reconstruction_method() == 'ByPlateId') or not all(f.get_left_plate() == plate_id or f.get_right_plate() == plate_id for f in features if f.get_reconstruction_method() in ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3']):
    raise ValueError("All features must have the same reconstruction plate ID, or Half-Stage must have one Id be the split plate")

  output_rc = FeatureCollection()

  to_add = []
  if left_plate_id != plate_id:
    to_add.extend(split_rotation_features_by_plate_id(rotation_features, plate_id, left_plate_id, split_time))
  if right_plate_id != plate_id:
    to_add.extend(split_rotation_features_by_plate_id(rotation_features, plate_id, right_plate_id, split_time))

  output_rc.add(to_add)

  rotation_model = RotationModel([f for f in rotation_features] + to_add)
  
  # Get rift geometry at split time
  rift_snapshot = ReconstructSnapshot([rift], rotation_model, split_time)
  rift_geometry = rift_snapshot.get_reconstructed_geometries()[0].get_reconstructed_geometry()
  
  if not isinstance(rift_geometry, PolylineOnSphere):
    raise TypeError("Rift feature must have PolylineOnSphere geometry")

  # Get feature geometries at split time
  features_snapshot = ReconstructSnapshot(features, rotation_model, split_time)
  feature_geometries = [rg.get_reconstructed_geometry() for rg in features_snapshot.get_reconstructed_geometries(same_order_as_reconstructable_features=True)]

  output_fc = FeatureCollection()
  
  # Process each feature
  for feature, geometry in zip(features, feature_geometries):
    feature_start, feature_end = feature.get_valid_time()
    feature_name = feature.get_name()
    
    # Split the feature based on its geometry type
    if isinstance(geometry, (PointOnSphere, MultiPointOnSphere)):
      left_features, right_features = _split_point_features(
        feature, geometry, rift_geometry, feature_name, feature_end, 
        split_time, plate_id, left_plate_id, right_plate_id, rotation_model
      )
    elif isinstance(geometry, PolylineOnSphere):
      left_features, right_features = _split_polyline_features(
        feature, geometry, rift_geometry, feature_name, feature_end,
        split_time, plate_id, left_plate_id, right_plate_id, rotation_model
      )
    elif isinstance(geometry, PolygonOnSphere):
      left_features, right_features = _split_polygon_features(
        feature, geometry, rift_geometry, feature_name, feature_end,
        split_time, plate_id, left_plate_id, right_plate_id, rotation_model
      )
    else:
      left_features, right_features = [], []
      # Unsupported geometry type, skip
      continue
    
    all_split_features = left_features + right_features
    # Dont need to reconstruct because functions handled it
    # reverse_reconstruct(all_split_features, rotation_model, split_time)
    output_fc.add(all_split_features)

  if generate_mor:
    output_fc.add(Feature.create_reconstructable_feature(
      FeatureType.gpml_mid_ocean_ridge, rift_geometry, f'MOR {split_time:.2f}',
      valid_time=(split_time, GeoTimeInstant.create_distant_future()),
      other_properties=[(PropertyName.gpml_reconstruction_method, Enumeration(
    EnumerationType.create_gpml('ReconstructionMethodEnumeration'),
    'HalfStageRotationVersion3')), (PropertyName.gpml_left_plate, GpmlPlateId(left_plate_id)), (PropertyName.gpml_right_plate, GpmlPlateId(right_plate_id))], reverse_reconstruct=(rotation_model, GeoTimeInstant(split_time))
    ))

  return output_fc, output_rc


def _determine_side_of_rift(point: PointOnSphere, rift_geometry: PolylineOnSphere) -> str:
  """
  Determine which side of the rift line a point is on.
  
  Args:
    point: The point to test
    rift_geometry: The rift line geometry
    
  Returns:
    'left', 'right', or 'on_rift' indicating the point's position
  """
  # Find the closest segment on the rift line
  min_distance = float('inf')
  closest_segment_idx = 0
  
  for i in range(len(rift_geometry) - 1):
    segment_start = rift_geometry[i]
    segment_end = rift_geometry[i + 1]
    segment_line = PolylineOnSphere([segment_start, segment_end])
    distance = PolylineOnSphere.distance(segment_line, point)
    
    if distance < min_distance:
      min_distance = distance
      closest_segment_idx = i

  # Get the closest segment
  segment_start = rift_geometry[closest_segment_idx]
  segment_end = rift_geometry[closest_segment_idx + 1]
  
  # Create great circle arc from segment start to point
  test_arc = GreatCircleArc(segment_start, point)
  segment_arc = GreatCircleArc(segment_start, segment_end)
  
  # Get directions at start point (t=0.0)
  test_direction = test_arc.get_arc_direction(0.0)
  segment_direction = segment_arc.get_arc_direction(0.0)
  
  # Calculate cross product to determine side
  cross_product = Vector3D.cross(segment_direction, test_direction)
  dot_product = Vector3D.dot(cross_product, segment_start.to_xyz())
  
  # Determine side based on dot product sign
  if abs(dot_product) < 1e-10:  # Very small threshold for "on the line"
    return 'on_rift'
  elif dot_product > 0:
    return 'left'
  else:
    return 'right'

def recreate_reconstructable_feature_with_method(old_feature: Feature, new_geometry: GeometryOnSphere, new_name: str, new_plate_id: int, old_plate_id: int, valid_time: tuple[float, float], rotation_model: RotationModel, split_time: float) -> Feature:
  method = old_feature.get_reconstruction_method()
  if method == 'ByPlateId':
    feature = Feature.create_reconstructable_feature(
        old_feature.get_feature_type(), new_geometry, new_name,
        valid_time=valid_time or old_feature.get_valid_time(), reconstruction_plate_id=int(new_plate_id), reverse_reconstruct=(rotation_model, GeoTimeInstant(split_time))
      )
    return feature
  if method in ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3']:
    left_plate = int(new_plate_id) if old_feature.get_left_plate() == int(old_plate_id) else old_feature.get_left_plate()
    right_plate = int(new_plate_id) if old_feature.get_right_plate() == int(old_plate_id) else old_feature.get_right_plate()
    feature = Feature.create_reconstructable_feature(
      old_feature.get_feature_type(), new_geometry, new_name,
      valid_time=valid_time or old_feature.get_valid_time(),
      other_properties=[
        (PropertyName.gpml_reconstruction_method, Enumeration(EnumerationType.create_gpml('ReconstructionMethodEnumeration'), method)),
        (PropertyName.gpml_left_plate, GpmlPlateId(left_plate)),
        (PropertyName.gpml_right_plate, GpmlPlateId(right_plate))
      ],
      reverse_reconstruct=(rotation_model, GeoTimeInstant(split_time))
    )
    return feature
  raise ValueError(f'Unknown reconstruction method: {method}')

def _split_point_features(feature: Feature, geometry, rift_geometry: PolylineOnSphere, 
                         feature_name: str, feature_end: float, split_time: float, old_plate_id: int,
                         left_plate_id: int, right_plate_id: int, rotation_model: RotationModel) -> tuple[list[Feature], list[Feature]]:
  """Split point or multipoint features based on rift line."""
  left_features = []
  right_features = []
  
  if isinstance(geometry, PointOnSphere):
    side = _determine_side_of_rift(geometry, rift_geometry)
    
    if side == 'left':
      left_feature = recreate_reconstructable_feature_with_method(
        feature, geometry, f'{feature_name} Left', left_plate_id, old_plate_id,
        valid_time=(split_time, feature_end), rotation_model=rotation_model, split_time=split_time
      )
      left_features.append(left_feature)
    elif side == 'right':
      right_feature = recreate_reconstructable_feature_with_method(
        feature, geometry, f'{feature_name} Right', right_plate_id, old_plate_id,
        valid_time=(split_time, feature_end), rotation_model=rotation_model, split_time=split_time
      )
      right_features.append(right_feature)
    # Points on the rift are not assigned to either side
    
  elif isinstance(geometry, MultiPointOnSphere):
    left_points = []
    right_points = []
    
    for point in geometry:
      side = _determine_side_of_rift(point, rift_geometry)
      if side == 'left':
        left_points.append(point)
      elif side == 'right':
        right_points.append(point)
      # Points on rift are not included
    
    if left_points:
      left_geometry = MultiPointOnSphere(left_points) if len(left_points) > 1 else PointOnSphere(left_points[0])
      left_feature = recreate_reconstructable_feature_with_method(
        feature, left_geometry, f'{feature_name} Left', left_plate_id, old_plate_id,
        valid_time=(split_time, feature_end), rotation_model=rotation_model, split_time=split_time
      )
      left_features.append(left_feature)
    
    if right_points:
      right_geometry = MultiPointOnSphere(right_points) if len(right_points) > 1 else PointOnSphere(right_points[0])
      right_feature = recreate_reconstructable_feature_with_method(
        feature, right_geometry, f'{feature_name} Right', right_plate_id, old_plate_id,
        valid_time=(split_time, feature_end), rotation_model=rotation_model, split_time=split_time
      )
      right_features.append(right_feature)
  
  return left_features, right_features


def _split_polyline_features(feature: Feature, geometry: PolylineOnSphere, rift_geometry: PolylineOnSphere,
                           feature_name: str, feature_end: float, split_time: float, old_plate_id: int,
                           left_plate_id: int, right_plate_id: int, rotation_model: RotationModel) -> tuple[list[Feature], list[Feature]]:
  """Split polyline features based on rift line intersection using line splitter."""
  left_features = []
  right_features = []
  
  # Use the line splitter to split the geometry by the rift line
  split_geometries = split_line_by(geometry, rift_geometry)
  
  # Classify each split segment by determining which side of the rift it's on
  for split_geometry in split_geometries:
    if len(split_geometry) < 2:  # Skip invalid segments
      continue
    
    # Determine side by checking the midpoint or centroid of the segment
    midpoint_idx = len(split_geometry) // 2
    midpoint = split_geometry[midpoint_idx]
    side = _determine_side_of_rift(midpoint, rift_geometry)
    
    # If the midpoint is on the rift, check other points
    if side == 'on_rift':
      for point in split_geometry:
        side = _determine_side_of_rift(point, rift_geometry)
        if side != 'on_rift':
          break
    
    # Create feature for the appropriate side
    if side == 'left':
      left_feature = recreate_reconstructable_feature_with_method(
        feature, split_geometry, f'{feature_name} Left', left_plate_id, old_plate_id,
        valid_time=(split_time, feature_end), rotation_model=rotation_model, split_time=split_time
      )
      left_features.append(left_feature)
    elif side == 'right':
      right_feature = recreate_reconstructable_feature_with_method(
        feature, split_geometry, f'{feature_name} Right', right_plate_id, old_plate_id,
        valid_time=(split_time, feature_end), rotation_model=rotation_model, split_time=split_time
      )
      right_features.append(right_feature)
    else:
      print(f'{feature_name} is entirely on the rift')
    # Segments exactly on the rift are not assigned to either side
  
  return left_features, right_features


def _split_polygon_features(feature: Feature, geometry: PolygonOnSphere, rift_geometry: PolylineOnSphere,
                          feature_name: str, feature_start: float, split_time: float, old_plate_id: int,
                          left_plate_id: int, right_plate_id: int, rotation_model: RotationModel) -> tuple[list[Feature], list[Feature]]:
  """Split polygon features based on rift line intersection using plate splitter."""
  left_features = []
  right_features = []
  
  try:
    # Use the plate splitter to split the polygon by the rift line
    split_polygons = split_plate_by_line(geometry, rift_geometry)
    
    # Classify each split polygon by determining which side of the rift it's on
    for split_polygon in split_polygons:
      try:
        # Use centroid to determine side
        centroid = split_polygon.get_centroid()
        side = _determine_side_of_rift(centroid, rift_geometry)
        
        # Should not happen in proper split
        if side == 'on_rift':
          point_sides = []
          for point in split_polygon:
            point_side = _determine_side_of_rift(point, rift_geometry)
            if point_side != 'on_rift':
              point_sides.append(point_side)
          
          # Use majority vote for side determination
          if len(point_sides):
            left_count = point_sides.count('left')
            right_count = point_sides.count('right')
            side = 'left' if left_count > right_count else 'right'
        
        # Create feature for the appropriate side
        if side == 'left':
          left_feature = recreate_reconstructable_feature_with_method(
            feature, split_polygon, f'{feature_name} Left', left_plate_id, old_plate_id,
            valid_time=(split_time, feature_start), rotation_model=rotation_model, split_time=split_time
          )
          left_features.append(left_feature)
        elif side == 'right':
          right_feature = recreate_reconstructable_feature_with_method(
            feature, split_polygon, f'{feature_name} Right', right_plate_id, old_plate_id,
            valid_time=(split_time, feature_start), rotation_model=rotation_model, split_time=split_time
          )
          right_features.append(right_feature)
        # Polygons exactly on the rift are not assigned to either side
        
      except Exception:
        # If processing fails for this polygon, skip it
        continue
  
  except Exception:
    pass
  
  return left_features, right_features