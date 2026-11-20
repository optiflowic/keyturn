#!/bin/sh
# keyturn's gate: runs the checks the project's stack profiles define, plus the guardrail checks.
# The logic is in gate.py next to this file; see ADR 0028 and `gate.sh --help`.
exec python3 "$(dirname "$0")/gate.py" "$@"
