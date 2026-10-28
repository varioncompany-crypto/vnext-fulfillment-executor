#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$root/scripts/prepare-workspace.sh"
test -f "$root/ROLE-REFERENCE.md"
test -d "$(dirname "$root")/varion-platform/.git"