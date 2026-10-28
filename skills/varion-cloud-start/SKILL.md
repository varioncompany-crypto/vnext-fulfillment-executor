---
name: varion-cloud-start
description: Start and verify this VARION cloud workspace for an assigned task.
---

# VARION cloud start

1. Verify the current checkout is the private role repository and read ROLE-REFERENCE.md for the role identity.
2. Check the adjacent varion-platform checkout. If absent, run bash scripts/prepare-workspace.sh once. If GitHub access fails, report the failing step.
3. Read the assigned task and current source state before changing files. Work in the existing shared project checkout for application code; keep this role repository for role setup.
4. Report exact repository commits, actual tool access, and the result. A successful checkout does not complete a business task.