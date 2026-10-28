#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$(dirname "$root")/varion-platform"
if [ -d "$target/.git" ]; then
  git -C "$target" status --short --branch
  exit 0
fi
GIT_TERMINAL_PROMPT=0 git clone https://github.com/varioncompany-crypto/varion-platform.git "$target"
git -C "$target" rev-parse HEAD
