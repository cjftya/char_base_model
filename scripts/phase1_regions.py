"""Polygon identities survive face ordering changes without positional labels."""
import hashlib
import json
from reference_common import ReferenceError


def face_key(vertices):
    # Winding may be reversed by normal correction; membership identifies a face.
    return ','.join(map(str, sorted(vertices)))


def capture(faces, labels):
    if len(faces) != len(labels):
        raise ReferenceError('Face/region counts differ')
    mapping = {}
    for face, label in zip(faces, labels):
        key = face_key(face)
        if key in mapping:
            raise ReferenceError('Duplicate face identity')
        mapping[key] = label
    return mapping


def resolve(faces, mapping):
    keys = [face_key(face) for face in faces]
    if len(keys) != len(set(keys)) or set(keys) != set(mapping):
        raise ReferenceError('Topology changed; explicitly replan region mapping')
    return [mapping[key] for key in keys]
