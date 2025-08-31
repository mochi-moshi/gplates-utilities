from pygplates import Feature, FeatureCollection, GpmlIrregularSampling, GpmlTimeSample, FiniteRotation, GpmlFiniteRotation, GpmlPlateId, PropertyName, FeatureReturn, RotationModel
from .utils import get_all_reconstruction_plate_ids

def create_initial_rotations(features: list[Feature], start_time: float, end_time: float):
    plate_ids = get_all_reconstruction_plate_ids(features)
    property_value = GpmlFiniteRotation(FiniteRotation.create_identity_rotation())
    return FeatureCollection([
        Feature.create_total_reconstruction_sequence(
            0, id,
            GpmlIrregularSampling(
              [
                GpmlTimeSample(property_value, end_time),
                GpmlTimeSample(property_value, start_time)
              ]
            )
        ) for id in plate_ids
    ])

# assumes no rotations after end_time
def replace_final_rotation(rotations: FeatureCollection, end_time: float = 0):
    plate_ids = set([f.get(PropertyName.gpml_moving_reference_frame).get_value().get_plate_id() for f in rotations])

    min_plate_time = {}
    for plate_id in plate_ids:
        features = rotations.get(lambda f: f.get(PropertyName.gpml_moving_reference_frame).get_value().get_plate_id() == plate_id, FeatureReturn.all)
        ref_id, _, samples = features[0].get_total_reconstruction_pole()
        samples.sort(lambda ts: -ts.get_time())
        min_plate_time[plate_id] = {
          'feature': features[0],
          'ref_id': ref_id,
          'samples': samples,
          'prev_feature': features[0],
          'prev_ref_id': ref_id,
          'prev_samples': samples
        }
        for feature in features[1:]:
            ref_id, _, samples = feature.get_total_reconstruction_pole()
            samples.sort(lambda ts: -ts.get_time())
            if samples[-1].get_time() < min_plate_time[plate_id]['samples'][-1].get_time():
                min_plate_time[plate_id] = {
                  'feature': feature,
                  'ref_id': ref_id,
                  'samples': samples,
                  'prev_feature': min_plate_time[plate_id]['feature'],
                  'prev_ref_id': min_plate_time[plate_id]['prev_ref_id'],
                  'prev_samples': min_plate_time[plate_id]['prev_samples']
                }
            elif samples[-1].get_time() < min_plate_time[plate_id]['prev_samples'][-1].get_time():
                min_plate_time[plate_id] = {
                  'prev_feature': feature,
                  'prev_ref_id': ref_id,
                  'prev_samples': samples
                }

    fc = FeatureCollection(rotations.get(lambda x: True, FeatureReturn.all))
    for plate_id, plate_data in min_plate_time.items():
        if plate_data['samples'][-1].get_time() != end_time:
            if len(plate_data['samples']) > 1:
                plate_data['samples'].append(GpmlTimeSample(plate_data['samples'][-2].get_value(), end_time))
                plate_data['samples'].sort(lambda ts: ts.get_time())
                feature = fc.get(lambda f: f.get_feature_id() == plate_data['feature'].get_feature_id())
                feature.set_total_reconstruction_pole(plate_data['ref_id'], plate_id, plate_data['samples'])
            else:
                plate_data['prev_samples'].append(GpmlTimeSample(plate_data['prev_samples'][-1].get_value(), end_time))
                plate_data['prev_samples'].sort(lambda ts: ts.get_time())
                feature = fc.get(lambda f: f.get_feature_id() == plate_data['prev_feature'].get_feature_id())
                feature.set_total_reconstruction_pole(plate_data['prev_ref_id'], plate_id, plate_data['prev_samples'])
        else:
            if len(plate_data['samples']) > 1:
                plate_data['samples'][-1] = GpmlTimeSample(plate_data['samples'][-2].get_value(), end_time)
                plate_data['samples'].sort(lambda ts: ts.get_time())
                feature = fc.get(lambda f: f.get_feature_id() == plate_data['feature'].get_feature_id())
                feature.set_total_reconstruction_pole(plate_data['ref_id'], plate_id, plate_data['samples'])
            else:
                plate_data['prev_samples'][-1] = GpmlTimeSample(plate_data['prev_samples'][-1].get_value(), end_time)
                plate_data['prev_samples'].sort(lambda ts: ts.get_time())
                feature = fc.get(lambda f: f.get_feature_id() == plate_data['prev_feature'].get_feature_id())
                feature.set_total_reconstruction_pole(plate_data['prev_ref_id'], plate_id, plate_data['prev_samples'])

    return fc

def split_rotation_features_by_plate_id(rotations: FeatureCollection, old_plate_id: int, new_plate_id: int, split_time: float):
    max_time = split_time
    min_time = split_time
    for rotation in rotations:
        _, rplate_id, sequence = rotation.get_total_reconstruction_pole()
        sequence.sort(lambda ts: ts.get_time())
        if rplate_id == old_plate_id:
            max_time = max(sequence[-1].get_time(), max_time)
            min_time = min(sequence[-1].get_time(), min_time)

    rotationsModel = RotationModel(rotations)

    # Already relative to default anchor_plate (0)
    start_rotation = rotationsModel.get_rotation(split_time, old_plate_id)
    end_rotation = rotationsModel.get_rotation(split_time, old_plate_id)

    rc = FeatureCollection()
    samples = GpmlIrregularSampling([GpmlTimeSample(GpmlFiniteRotation(end_rotation), min_time), GpmlTimeSample(GpmlFiniteRotation(start_rotation), split_time)])
    rc.add(Feature.create_total_reconstruction_sequence(0, new_plate_id, samples))
    rc.add(Feature.create_total_reconstruction_sequence(
        old_plate_id, new_plate_id,
        GpmlIrregularSampling([GpmlTimeSample(GpmlFiniteRotation(FiniteRotation.create_identity_rotation()), split_time)])
        )
    )
    if max_time != split_time:
        rc.add(Feature.create_total_reconstruction_sequence(
            old_plate_id, new_plate_id,
            GpmlIrregularSampling([GpmlTimeSample(GpmlFiniteRotation(FiniteRotation.create_identity_rotation()), max_time)])
            )
        )
    return rc

def create_new_rotation_plate(features: list[Feature], rotations: FeatureCollection, new_plate_id: int, split_time: float):
    if len(set([f.get_reconstruction_plate_id() for f in features])) > 1:
        raise ValueError(f'Features must all have the same plateId')

    fc = FeatureCollection()
    for feature in features:
        copy = feature.clone()
        copy.set_reconstruction_plate_id(new_plate_id)
        fc.add(copy)

    plateId = features[0].get_reconstruction_plate_id()

    max_time = split_time
    for rotation in rotations:
        _, rplate_id, sequence = rotation.get_total_reconstruction_pole()
        sequence.sort(lambda ts: ts.get_time())
        if rplate_id == plateId:
            max_time = max(sequence[-1].get_time(), max_time)

    new_rc = split_rotation_features_by_plate_id(rotations, plateId, new_plate_id, split_time)

    rc = rotations.clone()
    rc.add(new_rc)

    return fc, rc