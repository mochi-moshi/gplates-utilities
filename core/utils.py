from pygplates import FeatureCollection, Feature
from pygplates import PolylineOnSphere, PolygonOnSphere

PartitionResult = PolygonOnSphere.PartitionResult

import itertools


def is_valid(start: float, end: float, trange: tuple[float, float]):
    return start <= trange[0] > end and start > trange[1]


def lines_equal(a: PolylineOnSphere, b: PolylineOnSphere):
    return len(a) == len(b) and (
        all([p1 == p2 for p1, p2 in zip(a, b)])
        or all([p1 == p2 for p1, p2 in zip(a, b[::-1])])
    )


def generate_time_steps(
    rotation_features: FeatureCollection,
    plate_ids: set[int] | list[int],
    start_time: float,
    end_time: float,
    fixed_too: bool = True,
) -> list[tuple[float, float]]:
    """Generate time step ranges for subduction processing."""

    if fixed_too:
        new_ids = set(
            [
                fixed
                for fixed, moving, _ in (
                    f.get_total_reconstruction_pole() for f in rotation_features
                )
                if moving in plate_ids and fixed not in plate_ids
            ]
        )
        while new_ids:
            plate_ids = set(plate_ids).union(new_ids)
            new_ids = set(
                [
                    fixed
                    for fixed, moving, _ in (
                        f.get_total_reconstruction_pole() for f in rotation_features
                    )
                    if moving in new_ids and fixed not in new_ids
                ]
            )

    valid_rotation_times = set(
        itertools.chain.from_iterable(
            (s.get_time() for s in sequence)
            for _, moving, sequence in (
                f.get_total_reconstruction_pole() for f in rotation_features
            )
            if moving in plate_ids
        )
    )
    valid_rotation_times = sorted(valid_rotation_times, reverse=True)
    times = []

    for i in range(len(valid_rotation_times) - 1):
        if valid_rotation_times[i] <= end_time:
            break
        if valid_rotation_times[i + 1] >= start_time:
            continue
        start = (
            valid_rotation_times[i]
            if valid_rotation_times[i] <= start_time
            else start_time
        )
        end = (
            valid_rotation_times[i + 1]
            if valid_rotation_times[i + 1] >= end_time
            else end_time
        )
        times.append((start, end))

    return times


def get_all_reconstruction_plate_ids(features: list[Feature]) -> set[int]:
    return set(
        [
            f.get_reconstruction_plate_id()
            for f in features
            if f.get_reconstruction_method() == "ByPlateId"
        ]
        + [
            f.get_right_plate()
            for f in features
            if f.get_reconstruction_method()
            in [
                "HalfStageRotation",
                "HalfStageRotationVersion2",
                "HalfStageRotationVersion3",
            ]
        ]
        + [
            f.get_left_plate()
            for f in features
            if f.get_reconstruction_method()
            in [
                "HalfStageRotation",
                "HalfStageRotationVersion2",
                "HalfStageRotationVersion3",
            ]
        ]
    )
