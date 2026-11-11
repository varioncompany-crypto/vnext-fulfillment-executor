import ast
import tempfile
import unittest
from pathlib import Path
from fix_poll_readback import OLD, NEW, patched, install

COMMIT = 'a' * 40
BLOB = 'b' * 40


class CommitReadback(unittest.TestCase):
    def run_put(self, *, read_value=None, read_blob=BLOB, receipt=None, error=None):
        calls = []
        expected = {'version': 318, 'leaseOwner': 'synthetic-owner'}
        def api(method, path, body):
            calls.append(('write', method, body.get('sha')))
            if error:
                raise error
            return receipt if receipt is not None else {'commit': {'sha': COMMIT}, 'content': {'sha': BLOB}}
        def read(path, ref='main'):
            calls.append(('read', ref))
            return (read_value if read_value is not None else expected, read_blob) if ref == COMMIT else ({'version': 317}, 'c' * 40)
        namespace = {'api': api, 'read': read, 'R': 'example/repo'}
        exec('def put(p,x,sha=None):\n b={"sha":sha}\n ' + NEW, namespace)
        return lambda: namespace['put']('state.json', expected, 'd' * 40), calls

    def test_immutable_commit_ignores_stale_or_advanced_main(self):
        action, calls = self.run_put()
        self.assertEqual(action(), (COMMIT, BLOB))
        self.assertEqual(calls, [('write', 'PUT', 'd' * 40), ('read', COMMIT)])

    def test_content_mismatch_stops(self):
        action, calls = self.run_put(read_value={'version': 999})
        with self.assertRaisesRegex(RuntimeError, '^write_reconcile_required$'): action()
        self.assertEqual(len(calls), 2)

    def test_blob_mismatch_stops(self):
        action, _ = self.run_put(read_blob='e' * 40)
        with self.assertRaisesRegex(RuntimeError, '^write_reconcile_required$'): action()

    def test_missing_or_invalid_receipt_never_falls_back_to_main(self):
        for receipt in [{}, {'commit': {'sha': 'main'}, 'content': {'sha': BLOB}}, {'commit': {'sha': COMMIT}, 'content': None}]:
            action, calls = self.run_put(receipt=receipt)
            with self.assertRaisesRegex(RuntimeError, '^write_receipt_reconcile_required$'): action()
            self.assertEqual(len(calls), 1)

    def test_timeout_or_conflict_never_retries_write(self):
        for error in [TimeoutError('unknown outcome'), RuntimeError('github_http_409')]:
            action, calls = self.run_put(error=error)
            with self.assertRaises(type(error)): action()
            self.assertEqual(len(calls), 1)

    def test_guard_and_lease_logic_unchanged(self):
        source = "def put(p,x,sha=None):\n b={}\n " + OLD + "\ndef guard():\n return read('state.json')\n"
        result = patched(source)
        self.assertEqual(result.replace(NEW, OLD), source)
        ast.parse(result)
        self.assertEqual(patched(result), result)
        with self.assertRaisesRegex(ValueError, 'drift'): patched('different code')

    def test_local_backup_and_idempotent_install(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'poll.py'
            source = 'def put(p,x,sha=None):\n b={}\n ' + OLD + '\n'
            path.write_text(source, encoding='utf-8')
            self.assertTrue(install(path).startswith('patched_sha256='))
            self.assertEqual(path.with_name('poll.py.before-commit-readback').read_text(), source)
            self.assertEqual(install(path), 'already_patched')


if __name__ == '__main__': unittest.main()
