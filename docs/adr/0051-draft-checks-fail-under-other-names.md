# 0051. On a draft pull request, the gate's workflow fails its jobs under other names instead of skipping them

- Status: accepted
- Date: 2026-11-23
- Supersedes: in [0048](0048-default-branch-guarded-in-three-layers.md), that the gate's workflow skips draft pull requests ("The gate's CI runs only on pull requests that are not drafts"); in [0049](0049-workflow-runs-read-instead-of-check-runs.md), that the newest run for the commit by run ID is the one read, for the gate's workflow: it is now the newest among the runs with a job named as one of the checks

## Context

[ADR 0048](0048-default-branch-guarded-in-three-layers.md) had both jobs of the gate's workflow, `keyturn gate` and `keyturn conditions`, skip a draft pull request with a job-level condition, to keep a task within GitHub Free's included compute. It reasoned that GitHub does not merge a draft, and that neither `merge.py` nor `keyturn watch` counts a skipped check as a pass ([ADR 0049](0049-workflow-runs-read-instead-of-check-runs.md)).

Preparing the rehearsal (#63), a pull request opened as a draft and marked ready at once got two runs of the workflow on the same head: the draft's, with both jobs `skipped`, and the ready one's, with both jobs `failure`. The head then had two check runs named `keyturn gate` and two named `keyturn conditions`. The skipped ones were created later, although their run had the lower run ID, so `gh pr checks` showed them and printed "All checks were successful".

- GitHub counts a skipped job as passed for a required check: "A job that is skipped will report its status as "Success". It will not prevent a pull request from merging, even if it is a required check." Required checks "must have a `successful`, `skipped`, or `neutral` status".
- GitHub warns that "Using the same job name in multiple workflows can cause ambiguous status check results", and does not say which of two checks with the same name counts.

So where the plan has branch protection, a draft's skipped check can satisfy the required check that the run on the ready head failed. This is the reason [ADR 0043](0043-gate-finds-a-task-s-range-in-ci.md) gave the workflow no job-level condition ("a skipped required check counts as passed"); the draft condition of ADR 0048 brought it back. And `merge.py` and `keyturn watch` read the newest run for the head by run ID: a draft's run that is newer than the ready one does not pass, so it made them refuse a head whose checks passed.

## Options considered

1. **Keep skipping drafts.** No compute on drafts, but a skipped check with a required check's name stays on the head, and a person reads it as passed.
2. **Run the checks on drafts too.** Nothing is skipped, but a task's every push runs the gate with the profiles' tools, which ADR 0048 avoided for the compute.
3. **Fail a draft's jobs under the same names.** Nothing reads as passed, but two checks with the same name stay on the head, which GitHub calls ambiguous: the draft's failure can block a head whose checks passed.
4. **Fail a draft's jobs under other names.** On a draft, the jobs are named `keyturn gate (draft, not checked)` and `keyturn conditions (draft, not checked)`, and fail in their first step, before the checkout. A draft never gets a check with a required check's name.

## Decision

Option 4. The gate's workflow has no job-level condition. Each job's name is `keyturn gate` or `keyturn conditions` on a pull request that is not a draft, and the same name followed by ` (draft, not checked)` on a draft, where its first step fails with a message that a draft is not checked. `merge.py` and `keyturn watch` read the newest run of the gate's workflow for the head among those with a job named `keyturn gate` or `keyturn conditions`, instead of the newest of all its runs, and read it as ADR 0049 says otherwise; a run that lists no jobs yet (queued) or none at all is not passed over.

## Reasons

- It keeps ADR 0043's rule for the same reason: no check with a required check's name is ever skipped. On a draft there is none, so a required check waits ("Expected") instead of passing.
- A person who looks at a draft's checks sees them fail, with a name and a message that say why, and never reads them as passed.
- Marking the pull request ready runs both checks under their own names on the head, as before, and the merge conditions still need them only on the head that is merged (ADR 0048).
- Passing over a draft's runs keeps a draft's run that is newer than the ready one from stopping a merge whose checks passed, without counting it as anything.

## Consequences

- Each push of a draft runs two short jobs that fail in seconds. GitHub bills each job rounded up to the minute, so about 2 minutes per push: with 15 to 20 pushes in a task, about 30 to 40 minutes, under 2% of GitHub Free's 2,000 minutes a month for a private repository. A skipped job was not billed.
- A draft's checks are red. GitHub may notify whoever pushed about the failed runs.
- That the expression in a job's name reaches the check run's name, and the name the jobs API returns, is not in GitHub's documentation; the maintainer checks it on the rehearsal repository before the rehearsal (#153).
- `github/README.md` and the trial in `AGENTS.md` say what a draft's checks show.
