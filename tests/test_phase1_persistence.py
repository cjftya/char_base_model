"""Failure recovery for state publication."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from phase1_contract import replace_json, load

class PersistenceTests(unittest.TestCase):
    def test_serialization_failure_preserves_state_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            replace_json(path, {'state':'old'})
            with self.assertRaises(ValueError):
                replace_json(path, {'value':float('nan')})
            self.assertEqual(load(path), {'state':'old'})
            self.assertEqual(list(Path(directory).iterdir()), [path])
            replace_json(path, {'state':'new'})
            self.assertEqual(load(path), {'state':'new'})

    def test_publish_failure_preserves_state_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            replace_json(path, {'state':'old'})
            with patch.object(Path, 'replace', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    replace_json(path, {'state':'new'})
            self.assertEqual(load(path), {'state':'old'})
            self.assertEqual(list(Path(directory).iterdir()), [path])
