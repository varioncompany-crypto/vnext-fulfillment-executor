"""Narrow local patch; never runs the poller or calls a provider."""
from pathlib import Path
import ast
import hashlib
import sys

OLD = "r=api('PUT',f'repos/{R}/contents/{p}',b);rb,h=read(p);assert rb==x,'write_reconcile_required';return r['commit']['sha'],h"
NEW = """r=api('PUT',f'repos/{R}/contents/{p}',b)
 commit=r.get('commit',{}).get('sha');expected_blob=(r.get('content') or {}).get('sha')
 if not isinstance(commit,str) or len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise RuntimeError('write_receipt_reconcile_required')
 if not isinstance(expected_blob,str) or len(expected_blob)!=40 or any(c not in '0123456789abcdef' for c in expected_blob):raise RuntimeError('write_receipt_reconcile_required')
 rb,h=read(p,commit)
 if rb!=x or h!=expected_blob:raise RuntimeError('write_reconcile_required')
 return commit,h"""


def patched(source):
    if source.count(NEW) == 1 and OLD not in source:
        return source
    if source.count(OLD) != 1 or NEW in source:
        raise ValueError('poll_source_drift_preserved')
    result = source.replace(OLD, NEW)
    ast.parse(result)
    return result


def install(path):
    original = path.read_bytes()
    source = original.decode('utf-8')
    result = patched(source).encode('utf-8')
    if result == original:
        return 'already_patched'
    backup = path.with_name(path.name + '.before-commit-readback')
    if backup.exists() and backup.read_bytes() != original:
        raise ValueError('backup_conflict_preserved')
    if not backup.exists():
        with backup.open('xb') as stream:
            stream.write(original)
    candidate = path.with_name(path.name + '.commit-readback.pending')
    with candidate.open('xb') as stream:
        stream.write(result)
    if path.read_bytes() != original:
        candidate.unlink()
        raise ValueError('concurrent_local_change_preserved')
    candidate.replace(path)
    if path.read_bytes() != result:
        raise ValueError('local_readback_failed')
    return 'patched_sha256=' + hashlib.sha256(result).hexdigest()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: fix_poll_readback.py PATH_TO_EXISTING_POLL_PY')
    print(install(Path(sys.argv[1])))
