#!/bin/sh
# keyturn's merge conditions for a task's pull request: the review reports and the client's acceptance.
# The logic is in conditions.py next to this file; see ADR 0046 and `conditions.sh --help`.
exec python3 "$(dirname "$0")/conditions.py" "$@"
