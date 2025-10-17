from pygplates import (
    FeatureCollection,
    Feature,
    RotationModel,
    ReconstructSnapshot,
    FeatureType,
    reverse_reconstruct,
)
from pygplates import (
    PolylineOnSphere,
    PolygonOnSphere,
    GeoTimeInstant,
    PointOnSphere,
    PropertyName,
    Enumeration,
    EnumerationType,
    GeometryOnSphere,
    GpmlPlateId,
)
from ..utils import generate_time_steps

import numpy as np

PartitionResult = PolygonOnSphere.PartitionResult


def diverge(
    mid_ocean_ridge: Feature,
    rotation_features: FeatureCollection,
    start_time: float,
    end_time: float,
    *,
    use_topologies: bool = False,
):
    if not mid_ocean_ridge.get_reconstruction_method() in [
        "HalfStageRotation",
        "HalfStageRotationVersion2",
        "HalfStageRotationVersion3",
    ]:
        raise ValueError(
            f"Expected mid_ocean_ridge reconstruction method to be ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3'], got: {mid_ocean_ridge.get_reconstruction_method()}"
        )
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


def generate_ocean_crust_for_timestep(
    mid_ocean_ridge: Feature,
    plate_ids: set,
    rotation_model: RotationModel,
    older_time: float,
    younger_time: float,
) -> list[Feature]:
    """Generate ocean crust for a single time step using helper line approach"""

    # Get MOR geometry at start and end of time step
    mor_start = (
        ReconstructSnapshot([mid_ocean_ridge], rotation_model, older_time)
        .get_reconstructed_geometries()[0]
        .get_reconstructed_geometry()
    )
    mor_end = (
        ReconstructSnapshot([mid_ocean_ridge], rotation_model, younger_time)
        .get_reconstructed_geometries()[0]
        .get_reconstructed_geometry()
    )

    # Create helper lines for each plate (copies of start ridge geometry)
    helper_features = []
    for plate_id in plate_ids:
        # Create helper feature with ridge geometry attached to this plate
        helper_feature = Feature.create_reconstructable_feature(
            FeatureType.gpml_unclassified_feature,
            PolylineOnSphere(mor_start.get_points()),  # Copy of ridge geometry
            f"Helper Line Plate {plate_id}",
            valid_time=(older_time, younger_time),
            reconstruction_plate_id=plate_id,  # This attaches it to the plate
        )
        helper_features.append((plate_id, helper_feature))

    # Reverse reconstruct helper lines to present day, then forward reconstruct to end time
    # This simulates the helper lines moving with their plates
    helper_geometries = {}
    for plate_id, helper_feature in helper_features:
        # Move helper line to present day
        reverse_reconstruct([helper_feature], rotation_model, older_time)

        # Reconstruct helper line at end time (it has moved with the plate)
        helper_end_geometry = (
            ReconstructSnapshot([helper_feature], rotation_model, younger_time)
            .get_reconstructed_geometries()[0]
            .get_reconstructed_geometry()
        )
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
                FeatureType.gpml_oceanic_crust,
                ocean_crust_polygon,
                f"Ocean Crust Plate {plate_id} ({older_time} Mya)",
                valid_time=(
                    younger_time,
                    GeoTimeInstant.create_distant_future(),
                ),  # End time to distant future
                reconstruction_plate_id=plate_id,
            )

            ocean_crust_features.append(ocean_crust_feature)

    reverse_reconstruct(ocean_crust_features, rotation_model, younger_time)

    return ocean_crust_features


def divergeTriple(
    ridgeA: Feature,
    ridgeB: Feature,
    ridgeC: Feature,
    rotation_features: FeatureCollection,
    start_time: float,
    end_time: float,
    *,
    generate_new_plate: bool = False,
    use_topologies: bool = False,
):
    if not ridgeA.get_reconstruction_method() in [
        "HalfStageRotation",
        "HalfStageRotationVersion2",
        "HalfStageRotationVersion3",
    ]:
        raise ValueError(
            f"Expected ridgeA reconstruction method to be ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3'], got: {ridgeA.get_reconstruction_method()}"
        )
    if not ridgeB.get_reconstruction_method() in [
        "HalfStageRotation",
        "HalfStageRotationVersion2",
        "HalfStageRotationVersion3",
    ]:
        raise ValueError(
            f"Expected ridgeB reconstruction method to be ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3'], got: {ridgeB.get_reconstruction_method()}"
        )
    if not ridgeC.get_reconstruction_method() in [
        "HalfStageRotation",
        "HalfStageRotationVersion2",
        "HalfStageRotationVersion3",
    ]:
        raise ValueError(
            f"Expected ridgeC reconstruction method to be ['HalfStageRotation', 'HalfStageRotationVersion2', 'HalfStageRotationVersion3'], got: {ridgeC.get_reconstruction_method()}"
        )

    ridgeA_geometry = ridgeA.get_geometry()
    if not isinstance(ridgeA_geometry, PolylineOnSphere):
        raise TypeError("RidgeA must have PolylineOnSphere geometry")
    ridgeB_geometry = ridgeB.get_geometry()
    if not isinstance(ridgeB_geometry, PolylineOnSphere):
        raise TypeError("RidgeB must have PolylineOnSphere geometry")
    ridgeC_geometry = ridgeC.get_geometry()
    if not isinstance(ridgeC_geometry, PolylineOnSphere):
        raise TypeError("RidgeC must have PolylineOnSphere geometry")

    morA_start, morA_end = ridgeA.get_valid_time()
    morB_start, morB_end = ridgeB.get_valid_time()
    morC_start, morC_end = ridgeC.get_valid_time()
    start_time = min(morA_start, morB_start, morC_start, start_time)
    end_time = max(morA_end, morB_end, morC_end, end_time)

    plate_ids = set(
        [
            ridgeA.get_right_plate(),
            ridgeA.get_left_plate(),
            ridgeB.get_right_plate(),
            ridgeB.get_left_plate(),
            ridgeC.get_right_plate(),
            ridgeC.get_left_plate(),
        ]
    )

    if len(plate_ids) != 3:
        raise ValueError(
            f"Mid ocean ridges do not form triple juction, plate ids: {', '.join([str(p) for p in plate_ids])}"
        )

    rotation_model = RotationModel(rotation_features)

    times = generate_time_steps(rotation_features, plate_ids, start_time, end_time)

    ridge_a, ridge_b, ridge_c = [
        geom.get_reconstructed_geometry()
        for geom in ReconstructSnapshot(
            [ridgeA, ridgeB, ridgeC], rotation_model, times[0][0]
        ).get_reconstructed_geometries(same_order_as_reconstructable_features=True)
    ]

    output_fc = FeatureCollection()

    end_permutations = [
        (0, 0, 0),
        (-1, 0, 0),
        (0, -1, 0),
        (-1, -1, 0),
        (0, 0, -1),
        (-1, 0, -1),
        (0, -1, -1),
        (-1, -1, -1),
    ]
    distances = [
        PointOnSphere.distance(ridge_a[a], ridge_b[b])
        + PointOnSphere.distance(ridge_a[a], ridge_c[c])
        + PointOnSphere.distance(ridge_b[b], ridge_c[c])
        for a, b, c in end_permutations
    ]
    min_perm = (distances[0], end_permutations[0])
    for distance, permutation in zip(distances, end_permutations):
        if distance < min_perm[0]:
            min_perm = (distance, permutation)

    a_idx, b_idx, c_idx = min_perm[1]
    end_a = ridge_a[a_idx].to_xyz_array()[0]
    end_b = ridge_b[b_idx].to_xyz_array()[0]
    end_c = ridge_c[c_idx].to_xyz_array()[0]

    midpoint = (end_a + end_b + end_c) / 3
    length = np.sqrt(np.dot(midpoint, midpoint))
    if length == 0:
        raise ValueError(f"Points are equally spaced apart on sphere from start")

    midpoint /= length

    midpoint = PointOnSphere((midpoint[0], midpoint[1], midpoint[2]))

    ridges = [
        recreate_reconstructable_feature_with_method(ridgeA, midpoint, "RidgeA"),
        recreate_reconstructable_feature_with_method(ridgeB, midpoint, "RidgeB"),
        recreate_reconstructable_feature_with_method(ridgeC, midpoint, "RidgeC"),
    ]
    points = [
        Feature.create_reconstructable_feature(
            FeatureType.gpml_unclassified_feature,
            midpoint,
            f"Point {plate_id}",
            valid_time=(times[0][0], GeoTimeInstant.create_distant_future()),
            reconstruction_plate_id=plate_id,
        )
        for plate_id in plate_ids
    ]
    reverse_reconstruct(points, rotation_model, times[0][0])
    reverse_reconstruct(ridges, rotation_model, times[0][0])
    # output_fc.add(ridges)

    ridge_extentions = [
        recreate_reconstructable_feature_with_method(
            ridgeA, PolylineOnSphere([ridge_a[a_idx], midpoint]), ""
        ),
        recreate_reconstructable_feature_with_method(
            ridgeB, PolylineOnSphere([ridge_b[b_idx], midpoint]), ""
        ),
        recreate_reconstructable_feature_with_method(
            ridgeC, PolylineOnSphere([ridge_c[c_idx], midpoint]), ""
        ),
    ]
    reverse_reconstruct(ridge_extentions, rotation_model, times[0][0])

    ridge_extentions = [ridgeA, ridgeB, ridgeC] + ridge_extentions

    for older_time, younger_time in times:
        ridge_a, ridge_b, ridge_c = [
            geom.get_reconstructed_geometry()
            for geom in ReconstructSnapshot(
                ridges, rotation_model, younger_time
            ).get_reconstructed_geometries(same_order_as_reconstructable_features=True)
        ]
        end_a = ridge_a.to_xyz_array()[0]
        end_b = ridge_b.to_xyz_array()[0]
        end_c = ridge_c.to_xyz_array()[0]

        midpoint = (end_a + end_b + end_c) / 3
        length = np.sqrt(np.dot(midpoint, midpoint))
        if length == 0:
            print(
                f"Points are equally spaced apart on sphere for time steps {older_time} - {younger_time}"
            )
            continue

        midpoint /= length

        crusts, ridges, points = generateTripleJunctionCrust(
            PointOnSphere((midpoint[0], midpoint[1], midpoint[2])),
            ridges,
            [ridge_a, ridge_b, ridge_c],
            [
                geom.get_reconstructed_geometry()
                for geom in ReconstructSnapshot(
                    points, rotation_model, younger_time
                ).get_reconstructed_geometries(
                    same_order_as_reconstructable_features=True
                )
            ],
            plate_ids,
            older_time,
            younger_time,
        )

        new_ridge_extentions = [
            recreate_reconstructable_feature_with_method(
                ridgeA, PolylineOnSphere([ridge_a, midpoint]), ""
            ),
            recreate_reconstructable_feature_with_method(
                ridgeB, PolylineOnSphere([ridge_b, midpoint]), ""
            ),
            recreate_reconstructable_feature_with_method(
                ridgeC, PolylineOnSphere([ridge_c, midpoint]), ""
            ),
        ]
        reverse_reconstruct(new_ridge_extentions, rotation_model, younger_time)

        extra_crust = []
        for extention in ridge_extentions:
            extra_crust += generate_ocean_crust_for_timestep(
                extention,
                [extention.get_left_plate(), extention.get_right_plate()],
                rotation_model,
                older_time,
                younger_time,
            )

        ridge_extentions += new_ridge_extentions

        # points = []
        # points.append(
        #   Feature.create_reconstructable_feature(
        #     FeatureType.gpml_unclassified_feature ,
        #     PointOnSphere((midpoint[0], midpoint[1], midpoint[2])),
        #     f"Triple Midpoint ({older_time} Ma)",
        #     valid_time=(older_time, younger_time),  # End time to distant future
        #     reconstruction_plate_id=0
        #   )
        # )

        reverse_reconstruct(points, rotation_model, younger_time)
        reverse_reconstruct(crusts, rotation_model, younger_time)
        reverse_reconstruct(ridges, rotation_model, younger_time)

        output_fc.add(crusts)
        output_fc.add(extra_crust)
        # output_fc.add(ridges)
        # output_fc.add(points)

    return output_fc


def generateTripleJunctionCrust(
    midpoint: PointOnSphere,
    ridges: list[Feature],
    ridge_geoms: list[PointOnSphere],
    points: list[PointOnSphere],
    plate_ids: set[int],
    older_time: float,
    younger_time: float,
):
    plate_ids = list(plate_ids)

    plateA = [
        (ridge, geom)
        for ridge, geom in zip(ridges, ridge_geoms)
        if ridge.get_left_plate() == plate_ids[0]
        or ridge.get_right_plate() == plate_ids[0]
    ]
    plateB = [
        (ridge, geom)
        for ridge, geom in zip(ridges, ridge_geoms)
        if ridge.get_left_plate() == plate_ids[1]
        or ridge.get_right_plate() == plate_ids[1]
    ]
    plateC = [
        (ridge, geom)
        for ridge, geom in zip(ridges, ridge_geoms)
        if ridge.get_left_plate() == plate_ids[2]
        or ridge.get_right_plate() == plate_ids[2]
    ]

    crustA = Feature.create_reconstructable_feature(
        FeatureType.gpml_oceanic_crust,
        PolygonOnSphere([midpoint, plateA[0][1], points[0], plateA[1][1]]),
        f"Ocean Crust Plate {plate_ids[0]} ({younger_time} Mya)",
        valid_time=(younger_time, GeoTimeInstant.create_distant_future()),
        reconstruction_plate_id=plate_ids[0],
    )
    crustB = Feature.create_reconstructable_feature(
        FeatureType.gpml_oceanic_crust,
        PolygonOnSphere([midpoint, plateB[0][1], points[1], plateB[1][1]]),
        f"Ocean Crust Plate {plate_ids[1]} ({younger_time} Mya)",
        valid_time=(younger_time, GeoTimeInstant.create_distant_future()),
        reconstruction_plate_id=plate_ids[1],
    )
    crustC = Feature.create_reconstructable_feature(
        FeatureType.gpml_oceanic_crust,
        PolygonOnSphere([midpoint, plateC[0][1], points[2], plateC[1][1]]),
        f"Ocean Crust Plate {plate_ids[2]} ({younger_time} Mya)",
        valid_time=(younger_time, GeoTimeInstant.create_distant_future()),
        reconstruction_plate_id=plate_ids[2],
    )

    ridgeA = recreate_reconstructable_feature_with_method(
        ridges[0],
        midpoint,
        ridges[0].get_name(),
        valid_time=(younger_time, GeoTimeInstant.create_distant_future()),
    )
    ridgeB = recreate_reconstructable_feature_with_method(
        ridges[1],
        midpoint,
        ridges[1].get_name(),
        valid_time=(younger_time, GeoTimeInstant.create_distant_future()),
    )
    ridgeC = recreate_reconstructable_feature_with_method(
        ridges[2],
        midpoint,
        ridges[2].get_name(),
        valid_time=(younger_time, GeoTimeInstant.create_distant_future()),
    )

    points = [
        Feature.create_reconstructable_feature(
            FeatureType.gpml_unclassified_feature,
            midpoint,
            f"Point {plate_id}",
            valid_time=(younger_time, GeoTimeInstant.create_distant_future()),
            reconstruction_plate_id=plate_id,
        )
        for plate_id in plate_ids
    ]

    return [crustA, crustB, crustC], [ridgeA, ridgeB, ridgeC], points


def recreate_reconstructable_feature_with_method(
    old_feature: Feature,
    new_geometry: GeometryOnSphere,
    new_name: str,
    valid_time: tuple[float, float] = None,
):
    method = old_feature.get_reconstruction_method()
    if method == "ByPlateId":
        feature = Feature.create_reconstructable_feature(
            old_feature.get_feature_type(),
            new_geometry,
            new_name,
            valid_time=valid_time or old_feature.get_valid_time(),
            reconstruction_plate_id=old_feature.get_reconstruction_plate_id(),
        )
        return feature
    if method in [
        "HalfStageRotation",
        "HalfStageRotationVersion2",
        "HalfStageRotationVersion3",
    ]:
        feature = Feature.create_reconstructable_feature(
            old_feature.get_feature_type(),
            new_geometry,
            new_name,
            valid_time=valid_time or old_feature.get_valid_time(),
            other_properties=[
                (
                    PropertyName.gpml_reconstruction_method,
                    Enumeration(
                        EnumerationType.create_gpml("ReconstructionMethodEnumeration"),
                        method,
                    ),
                ),
                (
                    PropertyName.gpml_left_plate,
                    GpmlPlateId(old_feature.get_left_plate()),
                ),
                (
                    PropertyName.gpml_right_plate,
                    GpmlPlateId(int(old_feature.get_right_plate())),
                ),
            ],
        )
        return feature
