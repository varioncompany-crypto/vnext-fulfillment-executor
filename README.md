# vnext-fulfillment-executor
VARION Commerce &amp; Customer Cloud-Umgebung

## VARION Cloud-Arbeitsressourcen

Dieses Repository bindet die Kernrolle **vnext-fulfillment-executor**. Das Rollenprofil liegt in [ROLE-REFERENCE.md](ROLE-REFERENCE.md). Der gemeinsame Anwendungsquellcode bleibt im privaten Repository [varion-platform](https://github.com/varioncompany-crypto/varion-platform), damit die fünf Rollen nicht fünf auseinanderlaufende Kopien bearbeiten.

In einer autorisierten Codex-Cloud-Umgebung kann [scripts/prepare-workspace.sh](scripts/prepare-workspace.sh) den gemeinsamen Code als benachbartes Checkout bereitstellen. Das Skript enthält keine Zugangsdaten und bricht ab, wenn GitHub den Zugriff nicht erlaubt. Die Cloud-Umgebung muss separat veröffentlicht und ihr tatsächlicher Repositoryzugriff geprüft werden.

## Versioned customer-service reconciliation

The existing Operations schedule can invoke `python -B tools/customer_service_poll.py --run`
from its published role checkout. This replaces the absent scratch-only
`/workspace/work/cs-auto/poll.py` entry. It requires the existing authenticated `gh`
connection and `WILDLANDS_API_TOKEN`; it creates no schedule or queue.

The client checks that `vnext-ceo` is private, pins both current contracts to one
commit, and uses the existing `coordination/customer-service-autonomy-state.json`
with a GitHub Contents CAS lease of at most 15 minutes. Existing extensions,
intake attempts, retry fields and completed keys are preserved. It reads at most
ten inbox pages or 100 events, follows empty pages with cursors, refreshes owned
cases and stores only sanitized observation receipts in the existing result path.
The state references a result only after its immutable commit/blob readback.
Unknown writes are not retried. A conflicting, expired or superseded lease stops
progress; it never releases another owner's lease.

This is a reconciliation entry, not a business-action executor: it performs no
intake POST, customer message, moderation publication, refund, order, learning
submission, task transition or synthetic acceptance. The current recurring-intake
approval dependency remains recorded. Reading an approval does not complete a
case. Unsupported or unexecuted owned cases remain explicitly blocked; existing
completed references are only read and never promoted to new execution evidence.

Local validation: `python -B -m unittest discover -s tests -v` and
`python -B -m unittest discover -s tools -p 'test_poll_readback.py' -v`.
Running the script without `--run` has no network or coordination side effects.
Tests use only in-memory providers and temporary fixtures, never live intake.

A later runtime acceptance still requires publishing this exact role commit to
the existing environment, an ordinary existing hourly trigger, a fresh private
repository/contract read, successful owned lease acquisition, bounded real inbox
coverage, an immutable saved result and verification that its own lease was
released. Local tests, an uploaded commit and a manual start cannot prove that
unattended scheduled run. Run ID/trigger remain unknown unless actually exposed.
