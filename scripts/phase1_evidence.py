"""Evidence completeness and review freshness, independent of Blender."""
from pathlib import Path
from phase1_contract import digest, load
from reference_common import ReferenceError, VIEWS

REQUIRED = {'candidate.blend', 'metrics.json', 'alignment.json', 'review_context.json',
            'oblique_front.png', 'oblique_back.png'} | {v+'.png' for v in VIEWS} | {
                'overlay_'+v+'.png' for v in VIEWS}


def review_context(state):
    return {'state': state['state'], 'history_length': len(state['history']),
            'contract_sha256': state['contract_sha256'],
            'landmarks_sha256': state['landmarks_sha256']}


def validate_evidence(folder, state):
    folder = Path(folder)
    binding = load(folder / 'evidence.json')
    if not isinstance(binding, dict) or not REQUIRED <= binding.keys():
        raise ReferenceError('Review evidence is incomplete; collect all views again')
    for name, value in binding.items():
        if name in ('contract_sha256', 'landmarks_sha256'):
            if value != state.get(name):
                raise ReferenceError('Evidence input changed')
            continue
        if Path(name).name != name or '/' in name or '\\' in name or name in ('.', '..'):
            raise ReferenceError('Evidence paths must be local filenames')
        path = folder / name
        if path.is_symlink() or not path.is_file() or digest(path) != value:
            raise ReferenceError('Evidence artifact missing or changed: ' + name)
    if any(binding.get(k) != state.get(k) for k in ('contract_sha256', 'landmarks_sha256')):
        raise ReferenceError('Missing evidence input binding')
    if load(folder / 'review_context.json') != review_context(state):
        raise ReferenceError('Evidence belongs to a different stage or review attempt')
    return binding
