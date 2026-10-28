# vnext-fulfillment-executor
VARION Commerce &amp; Customer Cloud-Umgebung

## VARION Cloud-Arbeitsressourcen

Dieses Repository bindet die Kernrolle **vnext-fulfillment-executor**. Das Rollenprofil liegt in [ROLE-REFERENCE.md](ROLE-REFERENCE.md). Der gemeinsame Anwendungsquellcode bleibt im privaten Repository [varion-platform](https://github.com/varioncompany-crypto/varion-platform), damit die fünf Rollen nicht fünf auseinanderlaufende Kopien bearbeiten.

In einer autorisierten Codex-Cloud-Umgebung kann [scripts/prepare-workspace.sh](scripts/prepare-workspace.sh) den gemeinsamen Code als benachbartes Checkout bereitstellen. Das Skript enthält keine Zugangsdaten und bricht ab, wenn GitHub den Zugriff nicht erlaubt. Die Cloud-Umgebung muss separat veröffentlicht und ihr tatsächlicher Repositoryzugriff geprüft werden.
