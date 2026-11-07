"""Immutable model generations selected by one atomic state publication.

The canonical blend files live beside phase1_working.blend so relative assets
survive recovery without remapping. Working/final are derived views, not commits.
"""
from pathlib import Path
import os
import shutil
from contextlib import contextmanager
from uuid import uuid4
from phase1_contract import digest, load, replace_json
from reference_common import ReferenceError


def checkpoint_path(session, state):
    item = state.get('checkpoint')
    if not isinstance(item, dict):
        raise ReferenceError('Session has no committed checkpoint; initialize or migrate first')
    name = item.get('file', '')
    if Path(name).name != name or not name.startswith('phase1_generation_') or not name.endswith('.blend'):
        raise ReferenceError('Invalid checkpoint filename')
    path = Path(session) / name
    if path.is_symlink() or not path.is_file() or digest(path) != item.get('sha256'):
        raise ReferenceError('Committed model checkpoint is missing or modified')
    return path


@contextmanager
def writer_lock(session):
    """Serialize publication; a crash leaves an explicit recovery lock."""
    path = Path(session) / '.checkpoint.lock'
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ReferenceError('Checkpoint writer active or interrupted; inspect the lock before recovery') from exc
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


def publish(session, state, save_blend, *, expected_state):
    with writer_lock(session):
        return _publish(session, state, save_blend, expected_state=expected_state)


def _publish(session, state, save_blend, *, expected_state):
    """Save immutable model first; state.json is the only commit point.

    On failure before replacement, the previous committed pair remains intact.
    An unreferenced generation can be retained for investigation, never resumed.
    """
    session = Path(session)
    if load(session/'state.json') != expected_state:
        raise ReferenceError('Session state changed; reload before committing')
    generation = session / ('phase1_generation_' + uuid4().hex + '.blend')
    save_blend(generation)
    with generation.open('rb') as stream:
        os.fsync(stream.fileno())
    candidate = dict(state)
    candidate['checkpoint'] = {'file': generation.name, 'sha256': digest(generation)}
    if load(session/'state.json') != expected_state:
        raise ReferenceError('Concurrent session writer detected; new generation was not committed')
    replace_json(session/'state.json', candidate)
    return candidate


def materialize(session, state, filename='phase1_working.blend'):
    """Restore a derived file only from the committed generation."""
    session = Path(session)
    if filename not in ('phase1_working.blend', 'phase1_final.blend'):
        raise ReferenceError('Unsupported checkpoint output')
    if filename == 'phase1_final.blend' and state['state'] != 'PHASE1_COMPLETE':
        raise ReferenceError('Final output needs a committed COMPLETE state')
    source = checkpoint_path(session, state)
    target = session/filename
    if target.is_symlink():
        raise ReferenceError('Derived output cannot be a symlink')
    staged = session/('.recover-' + uuid4().hex + '.blend')
    try:
        shutil.copyfile(source, staged)
        with staged.open('rb') as stream:
            os.fsync(stream.fileno())
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)
    return target
