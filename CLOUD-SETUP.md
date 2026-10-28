# Codex Cloud configuration for vnext-fulfillment-executor

Description: VARION Kernrolle vnext-fulfillment-executor: privates Rollen-Repository mit gemeinsamem varion-platform Projektcode; Codex Cloud Arbeitsumgebung fuer autorisierte Entwicklungs- und Operationsauftraege.

Install script: bash scripts/install.sh

Start skill: skills/varion-cloud-start/SKILL.md

Environment variables: VARION_ROLE_KEY=vnext-fulfillment-executor and VARION_PLATFORM_REPO=varioncompany-crypto/varion-platform are non-secret identity hints. They do not grant API access.

Network secrets: None are stored in this repository. GitHub repository access must come from the connected company account. Add API credentials only through the protected environment secret controls after verifying the specific service, account, scope, and owner; never write values into GitHub.