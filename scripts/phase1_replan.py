"""Create a fresh measured draft/session; never mutate a failed generation."""
from pathlib import Path
import shutil
from phase1_contract import (load, digest, write_new, prepare_session, verify_sources,
                             validate_contract)
from phase1_checkpoint import checkpoint_path
from reference_common import ReferenceError


def prepare_replan(session, contract_path, landmarks_path, *, reason, destination=None):
    """Return REFERENCES_READY session with drafts, not accepted gate results.

    Run on the Blender host. Open the original Phase 0 file, initialize_working,
    then accept_landmarks using drafts/*.json. No failed mesh or review PASS is
    imported. Lineage is informational and contains exact parent fingerprints.
    """
    parent = Path(session).expanduser().resolve()
    if not isinstance(reason, str) or not reason.strip():
        raise ReferenceError('Explain the topology/measurement replan')
    if (parent/'.checkpoint.lock').exists():
        raise ReferenceError('Parent has an active/interrupted checkpoint writer')
    state = load(parent/'state.json')
    if state.get('status') not in ('REPLAN', 'BLOCKED'):
        raise ReferenceError('Replanning requires an explicitly halted session')
    verify_sources(parent)
    checkpoint = checkpoint_path(parent, state)
    files = {'state.json': digest(parent/'state.json'), checkpoint.name: digest(checkpoint),
             'phase0_source/inputs.json': digest(parent/'phase0_source/inputs.json')}
    for name, key in (('model_contract.json','contract_sha256'),
                      ('landmarks.json','landmarks_sha256'), ('head_spec.json','head_spec_sha256')):
        if state.get(key):
            if (parent/name).is_symlink() or digest(parent/name) != state[key]:
                raise ReferenceError('Parent accepted contract/landmarks changed')
            files[name] = state[key]
    contract, landmarks = load(contract_path), load(landmarks_path)
    validate_contract(contract, landmarks, state['sources'], require_head=False)
    records = load(parent/'phase0_source/inputs.json')
    manifest = load(records['manifest']['path'])
    if abs(contract['height_m'] - manifest['character_height_m']) > 1e-6:
        raise ReferenceError('Replanned height differs from Phase 0')
    if destination is not None:
        target = Path(destination).expanduser().resolve()
        if target == parent or parent in target.parents:
            raise ReferenceError('New session must be outside the preserved parent session')
    target = prepare_session(records['blend']['path'], records['manifest']['path'],
                             records['review']['path'], destination=destination)
    try:
        (target/'drafts').mkdir()
        write_new(target/'drafts/model_contract.json', contract)
        write_new(target/'drafts/landmarks.json', landmarks)
        # Preserve a compact inspectable parent snapshot without copying/claiming
        # its stale working file as the starting point of the new geometry.
        (target/'parent_snapshot').mkdir()
        for name in ('state.json', 'model_contract.json', 'landmarks.json', 'head_spec.json'):
            if name in files:
                shutil.copyfile(parent/name, target/'parent_snapshot'/name)
        lineage = {'parent_session': str(parent), 'parent_hashes': files,
                   'reason': reason, 'draft_contract_sha256': digest(target/'drafts/model_contract.json'),
                   'draft_landmarks_sha256': digest(target/'drafts/landmarks.json'),
                   'state': 'DRAFT', 'blender_validation': 'NOT RUN',
                   'source_mapping': records['images']}
        write_new(target/'replan.json', lineage)
        verify_sources(parent)
        if (parent/'.checkpoint.lock').exists() or any(digest(parent/name) != sha for name,sha in files.items()):
            raise ReferenceError('Parent changed during replanning; retry after inspection')
    except Exception:
        shutil.rmtree(target)
        raise
    return target
