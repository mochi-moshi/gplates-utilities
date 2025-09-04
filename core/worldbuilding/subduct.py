from pygplates import FeatureCollection, Feature, RotationModel, ReconstructSnapshot, FeatureType, reverse_reconstruct
from pygplates import PointOnSphere, MultiPointOnSphere, PolylineOnSphere, PolygonOnSphere, GeometryOnSphere, PropertyName, Enumeration, EnumerationType, GpmlPlateId, GeoTimeInstant
import itertools

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
    
    snapshots_older = ReconstructSnapshot(valid_features, rotation_model, older_time).get_reconstructed_geometries()
    snapshots_younger = ReconstructSnapshot(valid_features, rotation_model, younger_time).get_reconstructed_geometries()

    to_reconstruct_and_process = []
    to_reconstruct_and_add = []
    
    # Process each feature geometry
    for feature, snap_older, snap_younger in zip(valid_features, [s.get_reconstructed_geometry() for s in snapshots_older], [s2.get_reconstructed_geometry() for s2 in snapshots_younger]):
      
      geo_type = type(snap_younger).__name__
      feature_start, feature_end = feature.get_valid_time()
      feature_name = clean_feature_name(feature.get_name())
      
      # zone_area, ref_zone_area = create_zone_area(subduction_zone, rotation_model, older_time, younger_time, feature)

      zone_frames, ref_zone_frames = create_zone_frames(subduction_zone, rotation_model, older_time, younger_time, feature)

      # for zone in zone_frames:
      #   output_fc.add(Feature.create_reconstructable_feature(
      #     FeatureType.gpml_unclassified_feature, zone, f"Subzone {older_time} - {younger_time}",
      #     valid_time=(older_time, younger_time), reconstruction_plate_id=0
      #   ))
      # for ref_zone in ref_zone_frames:
      #   output_fc.add(Feature.create_reconstructable_feature(
      #     FeatureType.gpml_unclassified_feature, ref_zone, f"Ref Subzone {older_time} - {younger_time}",
      #     valid_time=(older_time, younger_time), reconstruction_plate_id=0
      #   ))

      # output_fc.add(Feature.create_reconstructable_feature(
      #   FeatureType.gpml_unclassified_feature, zone_area, f"Subzone {older_time} - {younger_time}",
      #   valid_time=(older_time, younger_time), reconstruction_plate_id=0
      # ))
      # output_fc.add(Feature.create_reconstructable_feature(
      #   FeatureType.gpml_unclassified_feature, ref_zone_area, f"Ref Subzone {older_time} - {younger_time}",
      #   valid_time=(older_time, younger_time), reconstruction_plate_id=0
      # ))

      if geo_type in ['PointOnSphere', 'MultiPointOnSphere']:
        alive_features, dead_features = process_point_geometry(
          feature, snap_older, snap_younger, zone_frames, ref_zone_frames, feature_name, feature_start, feature_end, younger_time
        )
        to_reconstruct_and_process.extend(alive_features)
        to_reconstruct_and_add.extend(dead_features)
        
      elif geo_type == 'PolylineOnSphere':
        alive_features, dead_features = process_polyline_geometry(
          feature, snap_older, snap_younger, zone_frames, ref_zone_frames, feature_name, feature_start, feature_end, younger_time
        )
        to_reconstruct_and_process.extend(alive_features)
        to_reconstruct_and_add.extend(dead_features)
        
      elif geo_type == 'PolygonOnSphere':
        alive_features, dead_features = process_polygon_geometry(
          feature, snap_older, snap_younger, zone_frames, ref_zone_frames, feature_name, feature_start, feature_end, younger_time
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

def create_zone_area(subduction_zone: Feature, rotation_model: RotationModel, older_time: float, younger_time: float, reference_feature: Feature = None) -> tuple[PolygonOnSphere, PolygonOnSphere]:
  """Create zone area polygon from subduction zone at two time points."""
  sz1 = ReconstructSnapshot([subduction_zone], rotation_model, older_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
  sz2 = ReconstructSnapshot([subduction_zone], rotation_model, younger_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
  zone = PolygonOnSphere(sz1[:] + sz2[::-1])
  ref_zone = None
  if reference_feature is not None:
    feature_by_ref = recreate_reconstructable_feature_with_method(reference_feature, sz1, '')
    reverse_reconstruct([feature_by_ref], rotation_model, older_time)
    sz3 = ReconstructSnapshot([feature_by_ref], rotation_model, younger_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
    ref_zone = PolygonOnSphere(sz1[:] + sz3[::-1])
  return zone, ref_zone

def create_zone_frames(subduction_zone: Feature, rotation_model: RotationModel, older_time: float, younger_time: float, reference_feature: Feature = None) -> tuple[list[PolygonOnSphere], list[PolygonOnSphere]]:
  """Create zone area polygon from subduction zone at two time points."""
  sz1 = ReconstructSnapshot([subduction_zone], rotation_model, older_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
  sz2 = ReconstructSnapshot([subduction_zone], rotation_model, younger_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()

  zones = []
  for s1, s2 in zip(sz1.get_segments(), sz2.get_segments()):
    zones.append(PolygonOnSphere([s2.get_end_point(), s2.get_start_point(), s1.get_start_point(), s1.get_end_point()]))
    
  ref_zones = []
  if reference_feature is not None:
    feature_by_ref = recreate_reconstructable_feature_with_method(reference_feature, sz1, '')
    reverse_reconstruct([feature_by_ref], rotation_model, older_time)
    sz3 = ReconstructSnapshot([feature_by_ref], rotation_model, younger_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
    for s1, s3 in zip(sz1.get_segments(), sz3.get_segments()):
      ref_zones.append(PolygonOnSphere([s3.get_end_point(), s3.get_start_point(), s1.get_start_point(), s1.get_end_point()]))
  return zones, ref_zones

def recreate_reconstructable_feature_with_method(old_feature: Feature, new_geometry: GeometryOnSphere, new_name: str, valid_time: tuple[float, float] = None):
  method = old_feature.get_reconstruction_method()
  if method == 'ByPlateId':
    feature = Feature.create_reconstructable_feature(
        old_feature.get_feature_type(), new_geometry, new_name,
        valid_time=valid_time or old_feature.get_valid_time(), reconstruction_plate_id=old_feature.get_reconstruction_plate_id()
      )
    return feature
  if method in ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3']:
    feature = Feature.create_reconstructable_feature(
      old_feature.get_feature_type(), new_geometry, new_name,
      valid_time=valid_time or old_feature.get_valid_time(),
      other_properties=[(PropertyName.gpml_reconstruction_method, Enumeration(
    EnumerationType.create_gpml('ReconstructionMethodEnumeration'),
    method)), (PropertyName.gpml_left_plate, GpmlPlateId(old_feature.get_left_plate())), (PropertyName.gpml_right_plate, GpmlPlateId(int(old_feature.get_right_plate())))]
    )
    return feature


def process_point_geometry(feature: Feature, snap_older, snap_younger, zone_frames: list[PolygonOnSphere], ref_zone_frames: list[PolygonOnSphere], feature_name: str, feature_start: float, feature_end: float, time2: float) -> tuple[list[Feature], list[Feature]]:
  """Process PointOnSphere or MultiPointOnSphere geometry for subduction."""
  geo_type = type(snap_younger).__name__
  to_reconstruct_and_process = []
  to_reconstruct_and_add = []
  
  paths = [PolylineOnSphere([snap_older, snap_younger])] if geo_type == 'PointOnSphere' else [PolylineOnSphere([p1, p2]) if p1 != p2 else p2 for p1, p2 in zip(snap_older, snap_younger)]
  points = [snap_older] if geo_type == 'PointOnSphere' else [p for p in snap_older]
  
  alive = []
  for path, point in zip(paths, points):
    alive = not any(zone.partition(path) in [PartitionResult.intersecting, PartitionResult.inside] for zone in zone_frames)
    alive = alive and not any(zone.is_point_in_polygon(point) for zone in ref_zone_frames)
    alive.append(alive)

  if geo_type == 'PointOnSphere':
    if alive[0]:
      to_reconstruct_and_process.append(
        recreate_reconstructable_feature_with_method(
          feature, PointOnSphere(snap_younger), f'{feature_name} Alive', 
          valid_time=(feature_start, feature_end)
        )
      )
    if not alive[0]:
      to_reconstruct_and_add.append(
        recreate_reconstructable_feature_with_method(
          feature, PointOnSphere(snap_younger), f'{feature_name} Dead', 
          valid_time=(feature_start, time2)
        )
      )
  else:
    if any(alive):
      to_reconstruct_and_process.append(
        recreate_reconstructable_feature_with_method(
          feature, MultiPointOnSphere([snap_younger[i] for i, is_alive in enumerate(alive) if is_alive]), 
          f'{feature_name} Alive', valid_time=(feature_start, feature_end)
        )
      )
    if not all(alive):
      to_reconstruct_and_add.append(
        recreate_reconstructable_feature_with_method(
          feature, MultiPointOnSphere([snap_younger[i] for i, is_alive in enumerate(alive) if not is_alive]), 
          f'{feature_name} Dead', valid_time=(feature_start, time2)
        )
      )

  return to_reconstruct_and_process, to_reconstruct_and_add

def process_polyline_segments_with_zone(snap_older, snap_younger, zone_frames: list[PolygonOnSphere]) -> tuple[list, list]:
  """Process polyline segments for subduction, returning valid and invalid segment paths."""
  segment_paths = [(s2, PolylineOnSphere([s2.get_start_point(), s2.get_end_point()]), PolygonOnSphere([s1.get_start_point(), s1.get_end_point(), s2.get_end_point(), s2.get_start_point()])) for s1, s2 in zip(snap_older.get_segments(), snap_younger.get_segments())]

  point_paths = [(s2, PolylineOnSphere([s1, s2])) for s1, s2 in zip(snap_older, snap_younger)]

  valid_segment_paths = []
  invalid_segment_paths = []

  for seg, seg_line, path in segment_paths:
    start_path = next((path for p, path in point_paths if p == seg.get_start_point()))
    end_path = next((path for p, path in point_paths if p == seg.get_end_point()))

    valid = [seg_line]
    
    for zone in zone_frames:
      start_subducted = zone.partition(start_path) in [PartitionResult.intersecting, PartitionResult.inside]
      end_subducted = zone.partition(end_path) in [PartitionResult.intersecting, PartitionResult.inside]
      subducted = zone.partition(path) in [PartitionResult.intersecting, PartitionResult.inside]

      if start_subducted and end_subducted:
        invalid_segment_paths.append(seg_line)
        valid = []
        break
      elif start_subducted:
        inside, outside = [], []
        for line in valid:
          zone.partition(line, inside, outside)
        valid = outside[1:]
        invalid_segment_paths.extend(inside + outside[0])
      elif end_subducted:
        inside, outside = [], []
        for line in valid:
          zone.partition(line, inside, outside)
        valid = outside[:-1]
        invalid_segment_paths.extend(inside + outside[-1])
      elif subducted:
        inside, outside = [], []
        for line in valid:
          zone.partition(line, inside, outside)
        valid = outside
        invalid_segment_paths.extend(inside)

    valid_segment_paths.extend(valid)

  return valid_segment_paths, invalid_segment_paths

def process_polylines_with_ref_zone(lines: list[PolylineOnSphere], ref_zone_frames: list[PolygonOnSphere]) -> tuple[list, list]:
  """Process polyline segments for subduction, returning valid and invalid segment paths."""
  valid_segment_paths = []
  invalid_segment_paths = []
  for line in lines:
    valid = [line]
    for zone in ref_zone_frames:
      tmp_valid = []
      for line in valid:
        zone.partition(line, invalid_segment_paths, tmp_valid)
      valid = tmp_valid
    valid_segment_paths.extend(valid)

  return valid_segment_paths, invalid_segment_paths

def calculate_subzone_path(snap_younger: PolygonOnSphere, zone_frames: list[PolygonOnSphere], ref_zone_frames: list[PolygonOnSphere]):
  """Calculate and add subzone path based on closest distance to valid segment."""

  zone_outline = PolylineOnSphere.join([PolylineOnSphere(zone_frames[0][:3][::-1])] + [PolylineOnSphere(zone[:2][::-1]) for zone in zone_frames[1:-1]] + [PolylineOnSphere(zone_frames[-1][:2][::-1]), PolylineOnSphere([zone_frames[-1][0], zone_frames[-1][-1]])])
  ref_zone_outline = PolylineOnSphere.join([PolylineOnSphere(ref_zone_frames[0][:3][::-1])] + [PolylineOnSphere(zone[:2][::-1]) for zone in ref_zone_frames[1:-1]] + [PolylineOnSphere(ref_zone_frames[-1][:2][::-1]), PolylineOnSphere([ref_zone_frames[-1][0], ref_zone_frames[-1][-1]])])

  internal_lines = []
  for i in range(len(zone_frames)):
    zone = zone_frames[i]
    ref_zone = ref_zone_frames[i]
    if i != len(zone_frames):
      internal_lines.append(PolylineOnSphere([zone[0], zone[-1], ref_zone[0]]))
    if i != 0:
      internal_lines.append(PolylineOnSphere([zone[1], zone[2], ref_zone[1]]))

  outlines = zone_outline + ref_zone_outline + internal_lines
  inside_path = []
  for zone_line in outlines:
    snap_younger.partition(zone_line, inside_path)
    
  # inside_path = PolylineOnSphere.join(inside_path)
  
  # selected_path = inside_path[0] if first_dist <= last_dist else inside_path[-1]
  subzone_paths = []
  for inside in inside_path:
    if not any([lines_equal(inside, path) for path in subzone_paths]):
      subzone_paths.append(inside)
  return subzone_paths

def merge_polygon_lines_with_subzones(polygon_lines: list, subzone_lines: list):
  """Merge polygon lines with subzone lines at connection points."""
  for i in range(len(polygon_lines)):
    for subzone_line in subzone_lines:
      if polygon_lines[i][0] == subzone_line[0]:
        polygon_lines[i] = PolylineOnSphere(subzone_line[::-1][:-1] + polygon_lines[i][:])
      elif polygon_lines[i][0] == subzone_line[-1]:
        polygon_lines[i] = PolylineOnSphere(subzone_line[:][:-1] + polygon_lines[i][:])
      elif polygon_lines[i][-1] == subzone_line[0]:
        polygon_lines[i] = PolylineOnSphere(polygon_lines[i][:] + subzone_line[:][1:])
      elif polygon_lines[i][-1] == subzone_line[-1]:
        polygon_lines[i] = PolylineOnSphere(polygon_lines[i][:] + subzone_line[::-1][1:])
        
      if polygon_lines[i][0] == polygon_lines[i][-1]:
        polygon_lines[i] = PolylineOnSphere(polygon_lines[i][:][:-1])

def process_polygon_geometry(feature: Feature, snap_older, snap_younger, zone_frames: list[PolygonOnSphere], ref_zone_frames: list[PolygonOnSphere], feature_name: str, feature_start: float, feature_end: float, time2: float) -> tuple[list[Feature], list[Feature]]:
  """Process PolygonOnSphere geometry for subduction."""
  to_reconstruct_and_process = []
  to_reconstruct_and_add = []
  
  pre_valid_segment_paths, invalid_segment_paths = process_polyline_segments_with_zone(snap_older, snap_younger, zone_frames)
  valid_segment_paths, extra_invalid_segment_paths = process_polylines_with_ref_zone(pre_valid_segment_paths, ref_zone_frames)
  
  subzone_paths = calculate_subzone_path(snap_younger, zone_frames, ref_zone_frames)

  subzone_lines = PolylineOnSphere.join(subzone_paths)
  valid_polygon_lines = PolylineOnSphere.join(valid_segment_paths)
  invalid_polygon_lines = PolylineOnSphere.join(invalid_segment_paths + extra_invalid_segment_paths)

  merge_polygon_lines_with_subzones(valid_polygon_lines, subzone_lines)
  merge_polygon_lines_with_subzones(invalid_polygon_lines, subzone_lines)
  
  # for line in outlines:
  #   to_reconstruct_and_process.append(Feature.create_reconstructable_feature(
  #     FeatureType.gpml_unclassified_feature, line, f'{feature_name} Subzone Edge',
  #     valid_time=(feature_start, feature_end), reconstruction_plate_id=0
  #   ))

  for line in valid_polygon_lines:
    to_reconstruct_and_process.append(
      recreate_reconstructable_feature_with_method(
        feature, PolygonOnSphere(line), f'{feature_name} Alive', 
        valid_time=(feature_start, feature_end)
      )
    )

  for line in invalid_polygon_lines:
    to_reconstruct_and_add.append(
      recreate_reconstructable_feature_with_method(
        feature, PolygonOnSphere(line), f'{feature_name} Dead', 
        valid_time=(feature_start, time2)
      )
    )

  return to_reconstruct_and_process, to_reconstruct_and_add

def process_polyline_geometry(feature: Feature, snap_older, snap_younger, zone_frames: list[PolygonOnSphere], ref_zone_frames: list[PolygonOnSphere], feature_name: str, feature_start: float, feature_end: float, time2: float) -> tuple[list[Feature], list[Feature]]:
  """Process PolylineOnSphere geometry for subduction."""
  to_reconstruct_and_process = []
  to_reconstruct_and_add = []
  
  pre_valid_segment_paths, pre_invalid_segment_paths = process_polyline_segments_with_zone(snap_older, snap_younger, zone_frames)

  valid_segment_paths, invalid_segment_paths = process_polylines_with_ref_zone(pre_valid_segment_paths, ref_zone_frames)
  
  pre_valid_lines = PolylineOnSphere.join(pre_valid_segment_paths)
  valid_lines = PolylineOnSphere.join(valid_segment_paths)
  
  # pre_invalid_lines = PolylineOnSphere.join(pre_invalid_segment_paths)
  invalid_lines = PolylineOnSphere.join(invalid_segment_paths + pre_invalid_segment_paths)

  # for line in pre_valid_lines:
  #   to_reconstruct_and_process.append(
  #     recreate_reconstructable_feature_with_method(
  #       feature, line, f'{feature_name} PreAlive', 
  #       valid_time=(feature_start, feature_end)
  #     )
  #   )
    
  for line in valid_lines:
    to_reconstruct_and_process.append(
      recreate_reconstructable_feature_with_method(
        feature, line, f'{feature_name} Alive', 
        valid_time=(feature_start, feature_end)
      )
    )
    
  # for line in pre_invalid_lines:
  #   to_reconstruct_and_add.append(
  #     recreate_reconstructable_feature_with_method(
  #       feature, line, f'{feature_name} PreDead', 
  #       valid_time=(feature_start, time2)
  #     )
  #   )
    
  for line in invalid_lines:
    to_reconstruct_and_add.append(
      recreate_reconstructable_feature_with_method(
        feature, line, f'{feature_name} Dead', 
        valid_time=(feature_start, time2)
      )
    )

  return to_reconstruct_and_process, to_reconstruct_and_add