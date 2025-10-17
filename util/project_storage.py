import json
import os
from typing import List

from core.session import Session
from util.subpath import is_subpath


def save_project(session: Session, filepath: str) -> bool:
    project_path = os.path.dirname(filepath)

    data = {}
    fc_paths: List[str] = []

    for fc in session.loaded_feature_collections:
        if is_subpath(fc.path, project_path):
            fc_paths.append(os.path.relpath(fc.path, project_path))
        else:
            fc_paths.append(fc.path)

    data["version"] = 1
    data["feature_collections"] = fc_paths

    if not session._rotationModel_path:
        data["rotation_model"] = ""
    elif is_subpath(session._rotationModel_path, project_path):
        data["rotation_model"] = os.path.relpath(
            session._rotationModel_path, project_path
        )
    else:
        data["rotation_model"] = session._rotationModel_path

    try:
        with open(filepath, "w") as file:
            json.dump(data, file, indent=4)
            return True
    except:
        return False


def load_project(session: Session, filepath: str) -> bool:
    project_path = os.path.dirname(filepath)
    data = {}

    try:
        with open(filepath, "r") as file:
            data = json.load(file)
    except:
        return False

    # TODO: Actually schema verification

    if data["version"] != 1:
        # TODO: set error to indicate invalid version
        return False

    fc_paths: List[str] = data["feature_collections"]

    for i in range(len(fc_paths)):
        if os.path.isabs(fc_paths[i]):
            continue
        fc_paths[i] = os.path.join(project_path, fc_paths[i])

    rotation_model: str = data["rotation_model"]

    if not os.path.isabs(rotation_model):
        rotation_model = os.path.join(project_path, rotation_model)

    session.load_feature_collections(fc_paths)
    session.load_rotation_model(rotation_model)
    session.set_project(filepath)

    return True
