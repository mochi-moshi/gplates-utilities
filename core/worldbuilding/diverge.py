from pygplates import FeatureCollection, Feature, RotationModel, ReconstructSnapshot, FeatureType, reverse_reconstruct
from pygplates import PolylineOnSphere, PolygonOnSphere, GeoTimeInstant
from ..utils import generate_time_steps

PartitionResult = PolygonOnSphere.PartitionResult

def diverge(mid_ocean_ridge: Feature, rotation_features: FeatureCollection, start_time: float, end_time: float, *, use_topologies: bool = False):
  if not mid_ocean_ridge.get_reconstruction_method() in ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3']:
    raise ValueError(f'Expected mid_ocean_ridge reconstruction method to be [\'HalfStageRotation\', \'HalfStageRotationVersion2\', \'HalfStageRotationVersion3\'], got: {mid_ocean_ridge.get_reconstruction_method()}')
  mor_start, mor_end = mid_ocean_ridge.get_valid_time()
  start_time = min(mor_start, start_time)
  end_time = max(mor_end, end_time)

  plate_ids = [mid_ocean_ridge.get_right_plate(), mid_ocean_ridge.get_left_plate()]
  
  mor_geometry = mid_ocean_ridge.get_geometry()
  if not isinstance(mor_geometry, PolylineOnSphere):
    raise TypeError("Mid-ocean ridge must have PolylineOnSphere geometry")

  rotation_model = RotationModel(rotation_features)

  times = generate_time_steps(rotation_features, plate_ids, start_time, end_time)

  output_fc = FeatureCollection()

  # Process each time step
  for older_time, younger_time in times:
    ocean_crust_features = generate_ocean_crust_for_timestep(
      mid_ocean_ridge, plate_ids, rotation_model, older_time, younger_time
    )
    output_fc.add(ocean_crust_features)

  return output_fc


def generate_ocean_crust_for_timestep(mid_ocean_ridge: Feature, plate_ids: set, 
                                    rotation_model: RotationModel, 
                                    older_time: float, younger_time: float) -> list[Feature]:
  """Generate ocean crust for a single time step using helper line approach"""
  
  # Get MOR geometry at start and end of time step
  mor_start = ReconstructSnapshot([mid_ocean_ridge], rotation_model, older_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
  mor_end = ReconstructSnapshot([mid_ocean_ridge], rotation_model, younger_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
  
  # Create helper lines for each plate (copies of start ridge geometry)
  helper_features = []
  for plate_id in plate_ids:
    # Create helper feature with ridge geometry attached to this plate
    helper_feature = Feature.create_reconstructable_feature(
      FeatureType.gpml_unclassified_feature,
      PolylineOnSphere(mor_start.get_points()),  # Copy of ridge geometry
      f"Helper Line Plate {plate_id}",
      valid_time=(older_time, younger_time),
      reconstruction_plate_id=plate_id  # This attaches it to the plate
    )
    helper_features.append((plate_id, helper_feature))
  
  # Reverse reconstruct helper lines to present day, then forward reconstruct to end time
  # This simulates the helper lines moving with their plates
  helper_geometries = {}
  for plate_id, helper_feature in helper_features:
    # Move helper line to present day
    reverse_reconstruct([helper_feature], rotation_model, older_time)
    
    # Reconstruct helper line at end time (it has moved with the plate)
    helper_end_geometry = ReconstructSnapshot([helper_feature], rotation_model, younger_time).get_reconstructed_geometries()[0].get_reconstructed_geometry()
    helper_geometries[plate_id] = helper_end_geometry
  
  # Generate ocean crust polygons
  ocean_crust_features = []
  for plate_id in plate_ids:
    helper_geometry = helper_geometries[plate_id]
    
    # Create polygon between helper line (old ridge position) and current ridge
    polygon_points = []
    polygon_points.extend(helper_geometry.get_points())
    polygon_points.extend(reversed(mor_end.get_points()))
    
    if len(polygon_points) >= 3:
      ocean_crust_polygon = PolygonOnSphere(polygon_points)
      
      # Create ocean crust feature with start time and distant future end time
      ocean_crust_feature = Feature.create_reconstructable_feature(
        FeatureType.gpml_unclassified_feature,  # Use unclassified since oceanic_crust may not be available
        ocean_crust_polygon,
        f"Ocean Crust Plate {plate_id} ({older_time} Ma)",
        valid_time=(younger_time, GeoTimeInstant.create_distant_future()),  # End time to distant future
        reconstruction_plate_id=plate_id
      )
      
      ocean_crust_features.append(ocean_crust_feature)
  
  reverse_reconstruct(ocean_crust_features, rotation_model, younger_time)
  
  return ocean_crust_features
