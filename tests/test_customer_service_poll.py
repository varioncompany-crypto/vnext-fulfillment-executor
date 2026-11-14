import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

spec = importlib.util.spec_from_file_location('poll', Path(__file__).parents[1] / 'tools/customer_service_poll.py')
poll = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poll)
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
REV = 'a' * 40


def initial():
    return {'kind': 'varion.customer-service-autonomy-state', 'schemaVersion': 1, 'version': 7,
            'leaseOwner': None, 'leaseExpiresAt': None, 'cursor': None,
            'processed': {'legacy-key': {'status': 'completed'}}, 'results': {}, 'retries': {},
            'sourceIntake': {'version': 1, 'sources': {'contacts': {'pending': {'attemptId': 'existing'}}}},
            'unknownExtension': {'preserve': True}}


class Git:
    def __init__(self):
        self.state = initial()
        self.version = 0
        self.writes = []
        self.values = {}
        self.on_put = None
        self.private_ok = True

    def private(self):
        if not self.private_ok:
            raise poll.Blocked('ceo_repository_not_private')

    def revision(self):
        return REV

    def read(self, path, revision=None):
        if path == poll.POLICY:
            return {'id': 'customer-policy', 'revision': 2, 'ownership': {'owner': 'operations'},
                    'technicalIntake': {'statePath': poll.STATE, 'recurringAcceptance': 'do not repeat'}}, 'p', REV
        if path == poll.INBOX:
            return {'api': {'list': 'GET /intelligence/company-events?cursor=<nextCursor>'}}, 'i', REV
        if path == poll.STATE:
            return copy.deepcopy(self.state), str(self.version), REV
        return copy.deepcopy(self.values[path]), 'result', REV

    def put(self, path, value, sha=None):
        if self.on_put:
            self.on_put(path, value)
        if path == poll.STATE:
            if sha != str(self.version):
                raise poll.Conflict('github_conflict')
            self.version += 1
            self.state = copy.deepcopy(value)
        else:
            if path in self.values:
                raise poll.Conflict('github_conflict')
            self.values[path] = copy.deepcopy(value)
        self.writes.append((path, copy.deepcopy(value)))
        return str(self.version), REV


class Inbox:
    def __init__(self, pages=None):
        self.pages = pages or [{'ok': True, 'events': [], 'nextCursor': None}]
        self.calls = []
        self.event = {'id': 'case-1', 'agent': 'vnext-fulfillment-executor',
                      'proposalHash': 'b' * 64, 'version': 2, 'synthetic': True,
                      'policyRevision': 2, 'decision': {'reason': 'private original reason'}}

    def get(self, path):
        self.calls.append(path)
        if path.startswith('/intelligence/company-events/'):
            return {'ok': True, 'event': copy.deepcopy(self.event)}
        return copy.deepcopy(self.pages.pop(0))


class LeaseAndReconciliation(unittest.TestCase):
    def make(self, git=None, inbox=None, now=lambda: NOW, operation='operations-test'):
        return poll.Poll(git or Git(), inbox or Inbox(), now=now, operation_id=operation)

    def test_existing_state_extensions_dedup_and_pending_intake_are_preserved(self):
        git = Git(); before = initial()
        out = self.make(git).run()
        self.assertEqual(out['status'], 'reconciled')
        self.assertIsNone(git.state['leaseOwner'])
        for key in ['processed', 'sourceIntake', 'unknownExtension', 'retries']:
            self.assertEqual(git.state[key], before[key])
        self.assertEqual(git.state['version'], 10)
        result = next(iter(git.values.values()))
        self.assertEqual(result['customerActions'], 0)
        self.assertEqual(result['intakePosts'], 0)
        self.assertFalse(result['acceptanceClaimed'])
        self.assertIsNone(result['schedulerRunId'])
        self.assertEqual(result['schedulerTrigger'], 'unknown')
        self.assertTrue(result['coverage']['complete'])
        self.assertEqual(git.state['lastPollResultRef'], out['resultRef'])

    def test_foreign_active_lease_has_no_writes_or_inbox_reads(self):
        git, inbox = Git(), Inbox()
        git.state.update(leaseOwner='someone-else', leaseExpiresAt=poll.stamp(NOW + timedelta(minutes=2)))
        self.assertEqual(self.make(git, inbox).run()['status'], 'skipped_foreign_lease')
        self.assertEqual(git.writes, [])
        self.assertEqual(inbox.calls, [])

    def test_expired_lease_can_be_acquired_with_cas(self):
        git = Git(); git.state.update(leaseOwner='expired', leaseExpiresAt=poll.stamp(NOW - timedelta(seconds=1)))
        self.assertEqual(self.make(git).run()['status'], 'reconciled')
        self.assertEqual(git.writes[0][1]['leaseOwner'], 'operations-test')
        self.assertEqual(poll.parsed_time(git.writes[0][1]['leaseExpiresAt']) - NOW, timedelta(minutes=15))

    def test_incompatible_state_or_intake_extension_never_written(self):
        for mutate in [lambda s: s.update(schemaVersion=99), lambda s: s.update(sourceIntake={'version': 99}),
                       lambda s: s.update(leaseOwner='inconsistent')]:
            git = Git(); mutate(git.state)
            with self.assertRaises(poll.Blocked): self.make(git).run()
            self.assertFalse(git.writes)

    def test_superseded_or_expired_guard_never_releases_foreign_lease(self):
        for mode in ['foreign', 'expiry', 'version']:
            git = Git(); inbox = Inbox(); client = self.make(git, inbox)
            original = inbox.get
            def get(path):
                if mode == 'foreign': git.state['leaseOwner'] = 'new-owner'
                elif mode == 'expiry': git.state['leaseExpiresAt'] = poll.stamp(NOW)
                else: git.version += 1
                return original(path)
            inbox.get = get
            with self.assertRaises(poll.Blocked): client.run()
            self.assertEqual(len(git.writes), 1)
            self.assertFalse(git.values)

    def test_definite_cas_conflict_is_retried_at_most_three_times(self):
        git = Git(); calls = []
        def conflict(path, value):
            calls.append(path)
            raise poll.Conflict('github_conflict')
        git.on_put = conflict
        with self.assertRaises(poll.Conflict): self.make(git).run()
        self.assertEqual(len(calls), 3)

    def test_uncertain_acquisition_is_not_retried(self):
        git = Git(); calls = []
        def lost(path, value):
            calls.append(path)
            git.state = copy.deepcopy(value)
            git.version += 1
            raise poll.Blocked('github_write_uncertain')
        git.on_put = lost
        with self.assertRaisesRegex(poll.Blocked, 'uncertain'): self.make(git).run()
        self.assertEqual(len(calls), 1)
        self.assertEqual(git.state['leaseOwner'], 'operations-test')

    def test_empty_filtered_page_follows_next_cursor_and_resets_after_complete(self):
        git = Git(); inbox = Inbox([{'events': [], 'nextCursor': 'page two'}, {'events': [], 'nextCursor': None}])
        self.make(git, inbox).run()
        self.assertEqual(inbox.calls, ['/intelligence/company-events', '/intelligence/company-events?cursor=page%20two'])
        self.assertIsNone(git.state['cursor'])

    def test_ten_page_limit_persists_continuation_without_complete_claim(self):
        git = Git(); inbox = Inbox([{'events': [], 'nextCursor': str(i)} for i in range(10)])
        self.make(git, inbox).run()
        self.assertEqual(git.state['cursor'], '9')
        self.assertFalse(next(iter(git.values.values()))['coverage']['complete'])

    def test_hundred_case_limit_never_reads_an_eleventh_or_extra_page(self):
        git = Git(); inbox = Inbox([{'events': [{'agent': 'other'}] * 100, 'nextCursor': 'remaining'}])
        self.make(git, inbox).run()
        receipt = next(iter(git.values.values()))
        self.assertEqual(receipt['coverage']['events'], 100)
        self.assertFalse(receipt['coverage']['complete'])
        self.assertEqual(git.state['cursor'], 'remaining')

    def test_approval_and_synthetic_event_are_observed_not_executed_or_completed(self):
        git = Git(); inbox = Inbox([{'events': [{'id': 'case-1', 'agent': 'vnext-fulfillment-executor'}], 'nextCursor': None}])
        self.make(git, inbox).run()
        record = next(iter(git.values.values()))['observations'][0]
        self.assertEqual(record['status'], 'blocked')
        self.assertTrue(record['synthetic'])
        self.assertEqual(git.state['processed'], initial()['processed'])
        self.assertNotIn('private original reason', json.dumps(git.values))
        self.assertIn('/intelligence/company-events/case-1', inbox.calls)

    def test_cursor_cycle_fails_without_progress_and_releases_own_lease(self):
        git = Git(); inbox = Inbox([{'events': [], 'nextCursor': 'repeat'}] * 2)
        with self.assertRaisesRegex(poll.Blocked, 'cycle'): self.make(git, inbox).run()
        self.assertIsNone(git.state['cursor'])
        self.assertIsNone(git.state['leaseOwner'])

    def test_non_private_repository_never_reads_inbox_or_writes(self):
        git = Git(); git.private_ok = False
        with self.assertRaisesRegex(poll.Blocked, 'not_private'): self.make(git).run()
        self.assertEqual(git.writes, [])


    def test_lost_progress_write_does_not_clear_uncertain_lease_or_retry(self):
        git = Git(); calls = []
        def lost(path, value):
            if path == poll.STATE and value['version'] == 9:
                calls.append(path)
                git.state = copy.deepcopy(value)
                git.version += 1
                raise poll.Blocked('github_write_uncertain')
        git.on_put = lost
        with self.assertRaisesRegex(poll.Blocked, 'github_write_uncertain'): self.make(git).run()
        self.assertEqual(len(calls), 1)
        self.assertEqual(git.state['leaseOwner'], 'operations-test')
        self.assertEqual(len(git.values), 1)
        self.assertEqual(git.state['processed'], initial()['processed'])

    def test_uncertain_result_write_is_not_repeated_and_cursor_stays(self):
        git = Git(); attempts = []
        def lost(path, value):
            if path.startswith(poll.RESULTS):
                attempts.append(path)
                git.values[path] = copy.deepcopy(value)
                raise poll.Blocked('github_write_uncertain')
        git.on_put = lost
        with self.assertRaisesRegex(poll.Blocked, 'uncertain'): self.make(git).run()
        self.assertEqual(len(attempts), 1)
        self.assertIsNone(git.state['cursor'])
        self.assertIsNone(git.state['leaseOwner'])
        self.assertEqual(git.state['results'], {})

    def test_replayed_operation_never_overwrites_an_existing_result(self):
        git = Git()
        self.make(git).run()
        with self.assertRaises(poll.Conflict): self.make(git).run()
        self.assertEqual(len(git.values), 1)
        self.assertIsNone(git.state['leaseOwner'])
        self.assertEqual(git.state['processed'], initial()['processed'])

    def test_case_owner_change_stops_before_result_or_progress_write(self):
        git = Git(); inbox = Inbox([{'events': [{'id': 'case-1', 'agent': 'operations'}], 'nextCursor': None}])
        inbox.event['agent'] = 'finance'
        with self.assertRaisesRegex(poll.Blocked, 'owner_changed'): self.make(git, inbox).run()
        self.assertEqual(git.values, {})
        self.assertIsNone(git.state['leaseOwner'])

    def test_contract_files_share_one_immutable_revision(self):
        git = Git(); calls = []; original = git.read
        def read(path, revision=None):
            calls.append((path, revision)); return original(path, revision)
        git.read = read
        poll.contracts(git)
        self.assertEqual(calls, [(poll.POLICY, REV), (poll.INBOX, REV)])

    def test_reader_has_no_business_or_intake_route(self):
        reader = poll.InboxReader()
        with self.assertRaisesRegex(poll.Blocked, 'route_not_allowed'):
            reader.get('/operations/service-intake/poll')


class ImmutableGitReadback(unittest.TestCase):
    def test_put_uses_returned_commit_and_blob_not_mutable_main(self):
        client = poll.GitHub(); calls = []
        value = {'synthetic': True}; blob = 'b' * 40
        def api(method, path, body=None):
            calls.append((method, path))
            return {'commit': {'sha': REV}, 'content': {'sha': blob}}
        def read(path, revision):
            calls.append(('READ', revision)); return value, blob, revision
        client.api, client.read = api, read
        self.assertEqual(client.put('fixture.json', value, 'old'), (blob, REV))
        self.assertEqual(calls[-1], ('READ', REV))

    def test_blob_or_content_mismatch_and_missing_receipt_stop(self):
        for mode in ['blob', 'content', 'receipt']:
            client = poll.GitHub()
            client.api = lambda *args: {} if mode == 'receipt' else {'commit': {'sha': REV}, 'content': {'sha': 'b' * 40}}
            client.read = lambda *args: ({'changed': mode == 'content'}, 'c' * 40 if mode == 'blob' else 'b' * 40, REV)
            with self.assertRaises(poll.Blocked): client.put('fixture.json', {'changed': False})


if __name__ == '__main__':
    unittest.main()
