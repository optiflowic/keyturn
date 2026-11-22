# 0050. The merge script also needs `keyturn watch` to have passed on the task's head

- Status: accepted
- Date: 2026-11-23

## Context

[ADR 0048](0048-default-branch-guarded-in-three-layers.md) has `keyturn watch` fail on a force push to a `task/**` branch, since [ADR 0043](0043-gate-finds-a-task-s-range-in-ci.md) trusts a task branch's history, and ties the layers together by having `merge.py` read the detecting check on the default branch's tip ("the failed check on the default branch's tip also stops `merge.py`").

A push to `task/**` starts `keyturn watch` on the pushed head, not on the default branch's tip. So a force push to the branch being merged makes the run on that head fail and open an issue, while the tip's last run, which started before the force push, still passed. `merge.py` read only the tip, and merged. The rewrite was found only by the next run on the default branch, after the merge (#149, second review stage).

## Options considered

1. **Keep ADR 0048 as it is.** The next run on the default branch finds the force push and opens an issue, but only after the task merged on a history the gate's range was found from.
2. **Also read `keyturn watch` on the task's head.** Every push of a task branch starts a run there; `merge.py` waits for the newest one and refuses when it failed.
3. **Refuse while any run of `keyturn watch` newer than the tip's passing run has failed.** Covers runs on other branches too, but a failure on another task's branch would then stop every merge, which the tip's run already does once it runs.

## Decision

Option 2. Besides the runs ADR 0048 and [ADR 0049](0049-workflow-runs-read-instead-of-check-runs.md) name, `merge.py` waits for the newest run of `.github/workflows/keyturn-watch.yml` for the pull request's head, read as ADR 0049 says (its run and its job `keyturn watch` concluded `success`), and refuses when it failed. A head with no run yet, or a run that has not finished, is waited for, within the same time as the other checks (exit 3 when it runs out).

## Reasons

- It closes the gap where it opens: the run that finds a force push to the task branch is the run on the head being merged.
- It costs no new run: the push right before the merge step starts it, and it runs while `merge.py` waits for the gate's run anyway.
- A failure stays in the activity until the maintainer moves the checkpoint (ADR 0048, "Recovering after a failed run"), so a later push that passes the history check still fails on the earlier force push.

## Consequences

- `merge.py` reads three runs: the gate's on the head, `keyturn watch` on the default branch's tip, and `keyturn watch` on the head.
- A push of the task branch that skipped workflows (`[skip ci]` in its message) leaves the head without a run, and the merge waits until the next push; `deliver` then stops for the maintainer, as for any check that does not finish.
- `github/README.md` and the `merge` step of `deliver` say so.
