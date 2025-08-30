from pygplates import FeatureCollection, Feature, RotationModel, ReconstructSnapshot, FeatureType, reverse_reconstruct
from pygplates import PointOnSphere, MultiPointOnSphere, PolylineOnSphere, PolygonOnSphere
from ..utils import generate_time_steps, lines_equal, is_valid, get_all_reconstruction_plate_ids

PartitionResult = PolygonOnSphere.PartitionResult

def subduct(features: list[Feature], subduction_zone: Feature, rotation_features: FeatureCollection, start_time: float, end_time: float, *, use_topologies: bool = False):
  """
  Process feature subduction through a subduction zone over time.
  
  Args:
    features: List of features to process for subduction
    subduction_zone: The subduction zone feature
    rotation_features: Collection of rotation features
    start_time: Start time for processing
    end_time: End time for processing
    
  Returns:
    FeatureCollection: Collection of processed features (alive and dead)
  """
  # Validate inputs and setup time range
  sz_start, sz_end = subduction_zone.get_valid_time()
  start_time = min(sz_start, start_time)
  end_time = max(sz_end, end_time)

  valid_features = [f for f in features if is_valid(start_time, end_time, f.get_valid_time())]
  fc = FeatureCollection(valid_features)
  if len(valid_features) == 0:
    return fc

  # Collect plate IDs and generate time steps
  plate_ids = get_all_reconstruction_plate_ids(valid_features)
  
  plate_ids.add(subduction_zone.get_reconstruction_plate_id())
  times = generate_time_steps(rotation_features, plate_ids, start_time, end_time)
  
  rotation_model = RotationModel(rotation_features)
  output_fc = FeatureCollection()

  # Process each time step
  for older_time, younger_time in times:
    zone_area = create_zone_area(subduction_zone, rotation_model, older_time, younger_time)
    sz2 = ReconstructSnapshot([subduction_zone], rotation_model, younger_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
    
    snapshot1 = ReconstructSnapshot(valid_features, rotation_model, older_time).get_reconstructed_geometries()
    snapshot2 = ReconstructSnapshot(valid_features, rotation_model, younger_time).get_reconstructed_geometries()

    to_reconstruct_and_process = []
    to_reconstruct_and_add = []
    
    # Process each feature geometry
    for feature, snap1, snap2 in zip(valid_features, [s.get_reconstructed_geometry() for s in snapshot1], [s2.get_reconstructed_geometry() for s2 in snapshot2]):
      geo_type = type(snap2).__name__
      plate_id = feature.get_reconstruction_plate_id()
      feature_start, feature_end = feature.get_valid_time()
      feature_name = clean_feature_name(feature.get_name())

      if geo_type in ['PointOnSphere', 'MultiPointOnSphere']:
        alive_features, dead_features = process_point_geometry(
          feature, snap1, snap2, zone_area, feature_name, feature_start, feature_end, plate_id, younger_time
        )
        to_reconstruct_and_process.extend(alive_features)
        to_reconstruct_and_add.extend(dead_features)
        
      elif geo_type == 'PolylineOnSphere':
        alive_features, dead_features = process_polyline_geometry(
          feature, snap1, snap2, zone_area, feature_name, feature_start, feature_end, younger_time
        )
        to_reconstruct_and_process.extend(alive_features)
        to_reconstruct_and_add.extend(dead_features)
        
      elif geo_type == 'PolygonOnSphere':
        alive_features, dead_features = process_polygon_geometry(
          feature, snap1, snap2, sz2, zone_area, feature_name, feature_start, feature_end, younger_time
        )
        to_reconstruct_and_process.extend(alive_features)
        to_reconstruct_and_add.extend(dead_features)

    # Reverse reconstruct features and add to output
    reverse_reconstruct(to_reconstruct_and_process, rotation_model, younger_time)
    reverse_reconstruct(to_reconstruct_and_add, rotation_model, younger_time)

    valid_features = to_reconstruct_and_process
    output_fc.add(to_reconstruct_and_add)
    
  output_fc.add(valid_features)
  return output_fc
  
def clean_feature_name(feature_name: str) -> str:
  """Remove 'Alive' or 'Dead' suffix from feature name."""
  if feature_name.endswith(' Alive'):
    return feature_name[:-6]
  elif feature_name.endswith(' Dead'):
    return feature_name[:-5]
  return feature_name

def create_zone_area(subduction_zone: Feature, rotation_model: RotationModel, time1: float, time2: float) -> PolygonOnSphere:
  """Create zone area polygon from subduction zone at two time points."""
  sz1 = ReconstructSnapshot([subduction_zone], rotation_model, time1).get_reconstructed_geometries()[0].get_reconstructed_geometry()
  sz2 = ReconstructSnapshot([subduction_zone], rotation_model, time2).get_reconstructed_geometries()[0].get_reconstructed_geometry()
  return PolygonOnSphere(sz1[:] + sz2[::-1])

def process_point_geometry(feature: Feature, snap1, snap2, zone_area: PolygonOnSphere, feature_name: str, feature_start: float, feature_end: float, plate_id: int, time2: float) -> tuple[list[Feature], list[Feature]]:
  """Process PointOnSphere or MultiPointOnSphere geometry for subduction."""
  geo_type = type(snap2).__name__
  to_reconstruct_and_process = []
  to_reconstruct_and_add = []
  
  paths = [PolylineOnSphere([snap1, snap2])] if geo_type == 'PointOnSphere' else [PolylineOnSphere([p1, p2]) if p1 != p2 else p2 for p1, p2 in zip(snap1, snap2)]
  
  alive = []
  for path in paths:
    results = zone_area.partition(path)
    alive.append(not (results == PartitionResult.intersecting or results == PartitionResult.inside))

  if geo_type == 'PointOnSphere':
    if alive[0]:
      to_reconstruct_and_process.append(
        Feature.create_reconstructable_feature(
          feature.get_feature_type(), PointOnSphere(snap2), f'{feature_name} Alive', 
          valid_time=(feature_start, feature_end), reconstruction_plate_id=plate_id
        )
      )
    if not alive[0]:
      to_reconstruct_and_add.append(
        Feature.create_reconstructable_feature(
          FeatureType.gpml_unclassified_feature, PointOnSphere(snap2), f'{feature_name} Dead', 
          valid_time=(feature_start, time2), reconstruction_plate_id=plate_id
        )
      )
  else:
    if any(alive):
      to_reconstruct_and_process.append(
        Feature.create_reconstructable_feature(
          feature.get_feature_type(), MultiPointOnSphere([snap2[i] for i, is_alive in enumerate(alive) if is_alive]), 
          f'{feature_name} Alive', valid_time=(feature_start, feature_end), reconstruction_plate_id=plate_id
        )
      )
    if not all(alive):
      to_reconstruct_and_add.append(
        Feature.create_reconstructable_feature(
          FeatureType.gpml_unclassified_feature, MultiPointOnSphere([snap2[i] for i, is_alive in enumerate(alive) if not is_alive]), 
          f'{feature_name} Dead', valid_time=(feature_start, time2), reconstruction_plate_id=plate_id
        )
      )

  return to_reconstruct_and_process, to_reconstruct_and_add

def process_polyline_segments(snap1, snap2, zone_area: PolygonOnSphere) -> tuple[list, list]:
  """Process polyline segments for subduction, returning valid and invalid segment paths."""
  segment_paths = [(s2, PolygonOnSphere([s1.get_start_point(), s1.get_end_point(), s2.get_end_point(), s2.get_start_point()])) for s1, s2 in zip(snap1.get_segments(), snap2.get_segments())]
  segment_paths = [(seg, zone_area.partition(path) in [PartitionResult.intersecting, PartitionResult.inside], path) for seg, path in segment_paths]

  point_paths = [(p2, zone_area.partition(PolylineOnSphere([p1, p2])) in [PartitionResult.intersecting, PartitionResult.inside]) for p1, p2 in zip(snap1, snap2)]
  valid_segment_paths = []
  invalid_segment_paths = []
  
  for seg, subducted, path in segment_paths:
    start_subducted = next((subducted for p, subducted in point_paths if p == seg.get_start_point()))
    end_subducted = next((subducted for p, subducted in point_paths if p == seg.get_end_point()))

    seg_line = PolylineOnSphere([seg.get_start_point(), seg.get_end_point()])

    if start_subducted and end_subducted:
      invalid_segment_paths.append(seg_line)
    elif start_subducted:
      inside, outside = [], []
      zone_area.partition(seg_line, inside, outside)
      valid_segment_paths.append(outside[-1])
      invalid_segment_paths.extend(inside + outside[:-1])
    elif end_subducted:
      inside, outside = [], []
      zone_area.partition(seg_line, inside, outside)
      valid_segment_paths.append(outside[-1])
      invalid_segment_paths.extend(inside + outside[:-1])
    elif subducted:
      inside, outside = [], []
      zone_area.partition(seg_line, inside, outside)
      valid_segment_paths.append(outside[-1])
      valid_segment_paths.append(outside[0])
      invalid_segment_paths.extend(inside + outside[1:-1])
    else:
      valid_segment_paths.append(seg_line)

  return valid_segment_paths, invalid_segment_paths

def calculate_subzone_path(snap2, sz2, valid_segment_paths: list, subzone_paths: list):
  """Calculate and add subzone path based on closest distance to valid segment."""
  inside_path = []
  snap2.partition(sz2, inside_path)
  inside_path = PolylineOnSphere.join(inside_path)
  
  if not inside_path or not valid_segment_paths:
    return
    
  first_dist = min(PointOnSphere.distance(inside_path[0][0], valid_segment_paths[-1][0]), 
                   PointOnSphere.distance(inside_path[0][0], valid_segment_paths[-1][1]), 
                   PointOnSphere.distance(inside_path[0][-1], valid_segment_paths[-1][0]), 
                   PointOnSphere.distance(inside_path[0][-1], valid_segment_paths[-1][1]))
  last_dist = min(PointOnSphere.distance(inside_path[-1][0], valid_segment_paths[-1][0]), 
                  PointOnSphere.distance(inside_path[-1][0], valid_segment_paths[-1][1]), 
                  PointOnSphere.distance(inside_path[-1][-1], valid_segment_paths[-1][0]), 
                  PointOnSphere.distance(inside_path[-1][-1], valid_segment_paths[-1][1]))
  
  selected_path = inside_path[0] if first_dist <= last_dist else inside_path[-1]
  if not any([lines_equal(selected_path, path) for path in subzone_paths]):
    subzone_paths.append(selected_path)

def merge_polygon_lines_with_subzones(polygon_lines: list, subzone_lines: list):
  """Merge polygon lines with subzone lines at connection points."""
  for i in range(len(polygon_lines)):
    for subzone_line in subzone_lines:
      if polygon_lines[i][0] == subzone_line[0]:
        polygon_lines[i] = PolylineOnSphere(subzone_line[1:][::-1] + polygon_lines[i][:])
      elif polygon_lines[i][0] == subzone_line[-1]:
        polygon_lines[i] = PolylineOnSphere(subzone_line[:-1] + polygon_lines[i][:])
      elif polygon_lines[i][-1] == subzone_line[0]:
        polygon_lines[i] = PolylineOnSphere(polygon_lines[i][:] + subzone_line[1:])
      elif polygon_lines[i][-1] == subzone_line[-1]:
        polygon_lines[i] = PolylineOnSphere(polygon_lines[i][:] + subzone_line[:-1][::-1])
        
      if polygon_lines[i][0] == polygon_lines[i][-1]:
        polygon_lines[i] = PolylineOnSphere(polygon_lines[i][:-1])

def process_polygon_geometry(feature: Feature, snap1, snap2, sz2, zone_area: PolygonOnSphere, feature_name: str, feature_start: float, feature_end: float, time2: float) -> tuple[list[Feature], list[Feature]]:
  """Process PolygonOnSphere geometry for subduction."""
  to_reconstruct_and_process = []
  to_reconstruct_and_add = []
  
  valid_segment_paths, invalid_segment_paths = process_polyline_segments(snap1, snap2, zone_area)
  
  # Calculate subzone paths for polygon
  segment_paths = [(s2, PolygonOnSphere([s1.get_start_point(), s1.get_end_point(), s2.get_end_point(), s2.get_start_point()])) for s1, s2 in zip(snap1.get_segments(), snap2.get_segments())]
  segment_paths = [(seg, zone_area.partition(path) in [PartitionResult.intersecting, PartitionResult.inside], path) for seg, path in segment_paths]
  point_paths = [(p2, zone_area.partition(PolylineOnSphere([p1, p2])) in [PartitionResult.intersecting, PartitionResult.inside]) for p1, p2 in zip(snap1, snap2)]
  
  subzone_paths = []
  for seg, subducted, path in segment_paths:
    start_subducted = next((subducted for p, subducted in point_paths if p == seg.get_start_point()))
    end_subducted = next((subducted for p, subducted in point_paths if p == seg.get_end_point()))
    
    if start_subducted and not end_subducted:
      calculate_subzone_path(snap2, sz2, valid_segment_paths, subzone_paths)
    elif end_subducted and not start_subducted:
      calculate_subzone_path(snap2, sz2, valid_segment_paths, subzone_paths)

  subzone_lines = PolylineOnSphere.join(subzone_paths)
  valid_polygon_lines = PolylineOnSphere.join(valid_segment_paths)
  invalid_polygon_lines = PolylineOnSphere.join(invalid_segment_paths)

  merge_polygon_lines_with_subzones(valid_polygon_lines, subzone_lines)
  merge_polygon_lines_with_subzones(invalid_polygon_lines, subzone_lines)

  for line in valid_polygon_lines:
    to_reconstruct_and_process.append(Feature.create_reconstructable_feature(
      feature.get_feature_type(), PolygonOnSphere(line), f'{feature_name} Alive', 
      valid_time=(feature_start, feature_end), reconstruction_plate_id=feature.get_reconstruction_plate_id()
    ))

  for line in invalid_polygon_lines:
    to_reconstruct_and_add.append(Feature.create_reconstructable_feature(
      FeatureType.gpml_unclassified_feature, PolygonOnSphere(line), f'{feature_name} Dead', 
      valid_time=(feature_start, time2), reconstruction_plate_id=feature.get_reconstruction_plate_id()
    ))

  return to_reconstruct_and_process, to_reconstruct_and_add

def process_polyline_geometry(feature: Feature, snap1, snap2, zone_area: PolygonOnSphere, feature_name: str, feature_start: float, feature_end: float, time2: float) -> tuple[list[Feature], list[Feature]]:
  """Process PolylineOnSphere geometry for subduction."""
  to_reconstruct_and_process = []
  to_reconstruct_and_add = []
  
  valid_segment_paths, invalid_segment_paths = process_polyline_segments(snap1, snap2, zone_area)
  
  valid_lines = PolylineOnSphere.join(valid_segment_paths)
  invalid_lines = PolylineOnSphere.join(invalid_segment_paths)

  for line in valid_lines:
    to_reconstruct_and_process.append(Feature.create_reconstructable_feature(
      FeatureType.gpml_unclassified_feature, line, f'{feature_name} Alive', 
      valid_time=(feature_start, feature_end), reconstruction_plate_id=feature.get_reconstruction_plate_id()
    ))
    
  for line in invalid_lines:
    to_reconstruct_and_add.append(Feature.create_reconstructable_feature(
      FeatureType.gpml_unclassified_feature, line, f'{feature_name} Dead', 
      valid_time=(feature_start, time2), reconstruction_plate_id=feature.get_reconstruction_plate_id()
    ))

  return to_reconstruct_and_process, to_reconstruct_and_add