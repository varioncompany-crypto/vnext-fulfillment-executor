"""Bounded company-inbox reconciliation using the existing private CEO register.

No intake POST, business execution, customer communication or synthetic acceptance.
The default command only explains the entry point; --run writes coordination receipts.
"""
import argparse
import base64
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

REPO = 'varioncompany-crypto/vnext-ceo'
STATE = 'coordination/customer-service-autonomy-state.json'
RESULTS = 'results/operations/customer-service-autonomy/'
HOST = 'https://wildlands-service.varioncompany.workers.dev'
POLICY = 'architecture/customer-service-workflow.2026-11-04.json'
INBOX = 'architecture/failsafe-company-inbox.v1.json'
SHA = re.compile(r'^[a-f0-9]{40}$')
OWNERS = {'operations', 'vnext-fulfillment-executor'}


class Blocked(RuntimeError):
    pass


class Conflict(Blocked):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def stamp(value):
    return value.isoformat().replace('+00:00', 'Z')


def parsed_time(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result
    except (AttributeError, TypeError, ValueError):
        raise Blocked('state_lease_invalid') from None


def validate_state(value):
    if (not isinstance(value, dict) or value.get('kind') != 'varion.customer-service-autonomy-state'
            or value.get('schemaVersion') != 1 or type(value.get('version')) is not int
            or value['version'] < 0):
        raise Blocked('state_schema_incompatible')
    if any(not isinstance(value.get(k), dict) for k in ('processed', 'results', 'retries')):
        raise Blocked('state_schema_incompatible')
    if value.get('cursor') is not None and not isinstance(value['cursor'], str):
        raise Blocked('state_cursor_invalid')
    owner, expiry = value.get('leaseOwner'), value.get('leaseExpiresAt')
    if (owner is None) != (expiry is None) or (owner is not None and not isinstance(owner, str)):
        raise Blocked('state_lease_invalid')
    if owner is not None:
        parsed_time(expiry)
    intake = value.get('sourceIntake')
    if intake is not None and (not isinstance(intake, dict) or intake.get('version') != 1):
        raise Blocked('state_intake_extension_incompatible')


class GitHub:
    def api(self, method, path, body=None):
        args = ['gh', 'api', '--method', method, path]
        if body is not None:
            args += ['--input', '-']
        try:
            result = subprocess.run(args, input=json.dumps(body) if body is not None else None,
                                    capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            raise Blocked('github_write_uncertain' if method == 'PUT' else 'github_read_failed') from None
        if result.returncode:
            if method == 'PUT' and 'HTTP 409' in result.stderr:
                raise Conflict('github_conflict')
            raise Blocked('github_write_uncertain' if method == 'PUT' else 'github_read_failed')
        try:
            return json.loads(result.stdout)
        except ValueError:
            raise Blocked('github_response_invalid') from None

    def private(self):
        if self.api('GET', f'repos/{REPO}').get('private') is not True:
            raise Blocked('ceo_repository_not_private')

    def revision(self):
        revision = self.api('GET', f'repos/{REPO}/commits/main').get('sha', '')
        if not SHA.fullmatch(revision):
            raise Blocked('github_revision_invalid')
        return revision

    def read(self, path, revision=None):
        revision = revision or self.revision()
        item = self.api('GET', f'repos/{REPO}/contents/{path}?ref={revision}')
        try:
            raw = base64.b64decode(item['content'], validate=False)
            if item.get('encoding') != 'base64' or len(raw) > 1000000:
                raise ValueError()
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if blob != item['sha']:
                raise ValueError()
            return json.loads(raw), item['sha'], revision
        except (KeyError, TypeError, ValueError):
            raise Blocked('github_blob_invalid') from None

    def put(self, path, value, sha=None):
        body = {'message': 'operations: customer-service reconciliation receipt',
                'content': base64.b64encode(json.dumps(value, sort_keys=True).encode()).decode()}
        if sha is not None:
            body['sha'] = sha
        # A write is never retried here, including timeout and ambiguous responses.
        reply = self.api('PUT', f'repos/{REPO}/contents/{path}', body)
        commit = reply.get('commit', {}).get('sha', '')
        blob = (reply.get('content') or {}).get('sha', '')
        if not SHA.fullmatch(commit) or not SHA.fullmatch(blob):
            raise Blocked('write_receipt_reconcile_required')
        readback, actual_blob, _ = self.read(path, commit)
        if actual_blob != blob or readback != value:
            raise Blocked('write_reconcile_required')
        return blob, commit


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class InboxReader:
    def get(self, path):
        if not path.startswith('/intelligence/company-events'):
            raise Blocked('worker_route_not_allowed')
        token = os.environ.get('WILDLANDS_API_TOKEN')
        if not token:
            raise Blocked('worker_credential_missing')
        request = urllib.request.Request(HOST + path, method='GET', headers={
            'Authorization': 'Bearer ' + token, 'User-Agent': 'VARION-Cloud-Integration/1.0'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=45) as response:
                raw = response.read(1000001)
            if len(raw) > 1000000:
                raise Blocked('worker_response_too_large')
            value = json.loads(raw)
            if not isinstance(value, dict) or value.get('ok') is not True:
                raise Blocked('worker_response_invalid')
            return value
        except urllib.error.HTTPError as error:
            raise Blocked('worker_http_' + str(error.code)) from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise Blocked('worker_read_failed') from None


def contracts(git):
    git.private()
    revision = git.revision()
    policy, _, _ = git.read(POLICY, revision)
    inbox, _, _ = git.read(INBOX, revision)
    if (not isinstance(policy.get('id'), str) or type(policy.get('revision')) is not int
            or policy['revision'] < 1
            or policy.get('ownership', {}).get('owner') != 'operations'
            or policy.get('technicalIntake', {}).get('statePath') != STATE
            or not policy.get('technicalIntake', {}).get('recurringAcceptance')
            or inbox.get('api', {}).get('list') != 'GET /intelligence/company-events?cursor=<nextCursor>'):
        raise Blocked('current_contract_incompatible')
    return revision, policy


class Poll:
    def __init__(self, git, inbox, now=utcnow, operation_id=None):
        self.git, self.inbox, self.now = git, inbox, now
        self.operation_id = operation_id or 'operations-' + str(uuid.uuid4())
        if not re.fullmatch(r'operations-[a-zA-Z0-9-]{1,100}', self.operation_id):
            raise Blocked('operation_id_invalid')
        self.sha = None

    def guard(self):
        state, sha, _ = self.git.read(STATE)
        validate_state(state)
        if (state.get('leaseOwner') != self.operation_id or sha != self.sha
                or parsed_time(state['leaseExpiresAt']) <= self.now()):
            raise Blocked('lease_lost_or_expired')
        return state

    def save(self, state):
        self.guard()
        value = copy.deepcopy(state)
        value['version'] += 1
        value['updatedAt'] = stamp(self.now())
        self.sha, _ = self.git.put(STATE, value, self.sha)
        self.guard()

    def acquire(self):
        # Only a definite CAS conflict permits another acquisition attempt.
        for attempt in range(3):
            state, sha, _ = self.git.read(STATE)
            validate_state(state)
            if state['leaseOwner'] is not None and parsed_time(state['leaseExpiresAt']) > self.now():
                return False
            state = copy.deepcopy(state)
            state.update(leaseOwner=self.operation_id,
                         leaseExpiresAt=stamp(self.now() + timedelta(minutes=15)),
                         updatedAt=stamp(self.now()), version=state['version'] + 1)
            try:
                self.sha, _ = self.git.put(STATE, state, sha)
                self.guard()
                return True
            except Conflict:
                if attempt == 2:
                    raise
        return False

    def inspect(self, event, state, policy):
        self.guard()
        identity = event.get('id')
        if not isinstance(identity, str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,200}', identity):
            raise Blocked('event_identity_invalid')
        fresh = self.inbox.get('/intelligence/company-events/' + urllib.parse.quote(identity, safe=''))
        event = fresh.get('event')
        if not isinstance(event, dict) or event.get('id') != identity:
            raise Blocked('event_readback_invalid')
        if event.get('agent') not in OWNERS:
            raise Blocked('event_owner_changed')
        proposal, version = event.get('proposalHash'), event.get('version')
        if not isinstance(proposal, str) or not re.fullmatch('[a-f0-9]{64}', proposal) or type(version) is not int:
            raise Blocked('event_version_invalid')
        # Existing processing records are preserved, never converted from an approval.
        completed = [x for x in state['processed'].values() if isinstance(x, dict)
                     and x.get('eventId') == identity and x.get('proposalHash') == proposal
                     and x.get('version') == version and x.get('status') == 'completed']
        verified = False
        for item in completed:
            ref = item.get('resultRef', '')
            match = re.fullmatch(r'https://github.com/' + re.escape(REPO)
                                 + r'/blob/([a-f0-9]{40})/(results/operations/customer-service-autonomy/[a-zA-Z0-9_.-]+\.json)', ref)
            if match:
                self.git.read(match[2], match[1])
                verified = True
        decision = event.get('decision')
        reason = decision.get('reason') if isinstance(decision, dict) else None
        reason_hash = hashlib.sha256(reason.encode()).hexdigest() if isinstance(reason, str) else None
        choice = decision.get('choice', decision.get('decision')) if isinstance(decision, dict) else None
        choice = choice if choice in ('approve', 'reject', 'acknowledge') else None
        return {'eventId': identity, 'proposalHash': proposal, 'version': version,
                'decisionChoice': choice,
                'synthetic': event.get('synthetic') is True,
                'decisionPresent': isinstance(decision, dict), 'decisionReasonSha256': reason_hash,
                'policyMatches': event.get('policyRevision') in (policy.get('revision'), policy.get('id') + ':' + str(policy.get('revision'))),
                'existingCompletedResultRead': verified,
                'status': 'observed_existing_result' if verified else 'blocked',
                'blocker': None if verified else 'business_execution_not_implemented_in_reconciliation_poller'}

    def run(self):
        revision, policy = contracts(self.git)
        if not self.acquire():
            return {'status': 'skipped_foreign_lease', 'wrote': False}
        try:
            state = self.guard()
            cursor, pages, count, seen, observations = state['cursor'], 0, 0, set(), []
            while pages < 10 and count < 100:
                self.guard()
                path = '/intelligence/company-events'
                if cursor is not None:
                    path += '?cursor=' + urllib.parse.quote(cursor, safe='')
                page = self.inbox.get(path)
                events, next_cursor = page.get('events'), page.get('nextCursor')
                if (not isinstance(events, list) or len(events) > 100 - count
                        or next_cursor is not None and not isinstance(next_cursor, str)):
                    raise Blocked('inbox_page_invalid')
                pages += 1
                for event in events:
                    if not isinstance(event, dict):
                        raise Blocked('inbox_event_invalid')
                    count += 1
                    if event.get('agent') in OWNERS:
                        observations.append(self.inspect(event, state, policy))
                cursor = next_cursor
                if cursor is None:
                    break
                if cursor in seen:
                    raise Blocked('inbox_cursor_cycle')
                seen.add(cursor)
            receipt = {'schemaVersion': 1, 'kind': 'customer_service_reconciliation',
                       'operationId': self.operation_id, 'rulesRevision': revision,
                       'observedAt': stamp(self.now()), 'schedulerRunId': None,
                       'schedulerTrigger': 'unknown', 'coverage': {'pages': pages, 'events': count,
                       'complete': cursor is None}, 'observations': observations,
                       'customerActions': 0, 'intakePosts': 0, 'acceptanceClaimed': False,
                       'blockers': ['recurring_intake_approval_dependency',
                                    'business_actions_require_separate_verified_executor']}
            self.guard()
            path = RESULTS + 'poll-' + self.operation_id + '.json'
            _, commit = self.git.put(path, receipt)
            result_ref = 'https://github.com/' + REPO + '/blob/' + commit + '/' + path
            # A result commit readback proves persistence, not current lease ownership.
            state = self.guard()
            state['cursor'] = cursor
            state['lastPollResultRef'] = result_ref
            state['results'][self.operation_id] = result_ref
            self.save(state)
            return {'status': 'reconciled', 'resultRef': result_ref, 'leaseReleased': True,
                    'operationId': self.operation_id, 'customerActions': 0}
        finally:
            # Never clear a foreign, expired, superseded or uncertain lease.
            pending_error = sys.exc_info()[0] is not None
            try:
                state = self.guard()
            except Blocked:
                if not pending_error:
                    raise
            else:
                state['leaseOwner'] = None
                state['leaseExpiresAt'] = None
                value = copy.deepcopy(state)
                value['version'] += 1
                value['updatedAt'] = stamp(self.now())
                self.sha, _ = self.git.put(STATE, value, self.sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='read inbox; write only existing coordination state/results')
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({'entryPoint': 'tools/customer_service_poll.py --run', 'customerActions': False,
                          'intakePosts': False, 'runtimeAcceptance': False}))
        return 0
    try:
        print(json.dumps(Poll(GitHub(), InboxReader()).run()))
        return 0
    except Exception as error:
        # Provider bodies, contract text and customer data must not enter logs.
        code = str(error) if isinstance(error, Blocked) else 'poll_failed_reconcile_before_retry'
        print(json.dumps({'status': 'blocked', 'error': code, 'runtimeAcceptance': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
