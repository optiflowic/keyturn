# 0028. The gate is a Python CLI behind `gates/gate.sh`, run on a Git range, with JSON stack profiles

- Status: accepted; the design and the ADRs read at the base, when `--others` names a document role's commit, superseded by [0032](0032-gate-base-is-where-the-task-branch-left.md); the list of profile fields superseded by [0037](0037-gate-records-tool-versions.md) (also `versions`) [0040](0040-profile-tools-at-conventions-versions.md) (also `pinned`), and [0056](0056-gate-fails-new-packages-with-install-scripts.md) (also `install_scripts`); a suppression approved only by an ADR its line names superseded by [0038](0038-suppressions-allowed-in-a-folder.md) (also by an ADR that allows it in the file's folder)
- Date: 2026-11-21

## Context

"Gates" in [`docs/design/architecture.md`](../design/architecture.md#gates) says that `gates/gate.sh` is a plain CLI, independent of Claude Code and Codex, called by `deliver` and by CI, that reads the stack profile to decide what to run and says how to install a missing tool. "Guardrails" 1 ([`docs/design/guardrails.md`](../design/guardrails.md)) lists what it must catch: developer changes to protected paths, new suppression comments without an approved decision record, and a drop in the number of tests. The MVP (#114) needs that much, for the `go` and `react-spa` profiles ([ADR 0003](0003-first-stack-profiles.md)), before the profiles exist.

Questions to settle: what the gate is written in, how it is called and what it returns, how a project says which profile applies to which folder, what a profile holds, and how a suppression is approved.

## Options considered

1. **Language.**
   - **All in a shell script**: no interpreter beyond the shell, but parsing a diff, reading JSON, and comparing counts in `sh` is fragile, differs between macOS and Linux tools, and is hard to test.
   - **`gate.sh` as the entry, the logic in `gates/gate.py`** (standard library only, Python 3.9 or later, like `localize` and `project-config`, [ADR 0006](0006-localize-helper-script.md), [ADR 0014](0014-project-configuration-in-json.md)): the documented command stays `gate.sh`, and the logic is tested with `unittest`.
2. **Which profile applies where.**
   - **The design's "Stack" section**: one place for people, but the gate would parse a Markdown table that people and agents write freely.
   - **A `parts` setting in `keyturn/config.json`**, checked by `project-config` ([ADR 0014](0014-project-configuration-in-json.md)): read by a JSON parser, and checked before use.
3. **How a suppression is approved.**
   - **No exceptions in the MVP**: simplest, but a justified suppression would send the work back with no way out.
   - **A table of allowed suppressions in the design**: one more section for the gate to parse.
   - **The same line names an accepted ADR of the project** (for example `//nolint:gosec // ADR-0005`): the approval is visible where the suppression is, and the gate can check it.

## Decision

For the first two questions, option 2; for the third, the last option, with the ADR naming what it allows.

**Call.** `gates/gate.sh --base <rev> [--head <rev>] [--log <file>] [--profiles <dir>] [--timeout-minutes <n>]`, run from inside the project's repository. The base and the head are each checked out in a temporary worktree, and every check reads those, never the working tree, so only what is committed counts (an ignored or uncommitted file cannot change a result). A part's folder that leads outside its worktree (a symbolic link) fails that part's checks. Every command the gate runs, the profile's included, gets the caller's environment without Git's `GIT_*` variables, which could point it at another repository. `--head` defaults to `HEAD`, `--profiles` to the plugin's `profiles/`, and each command's limit to 30 minutes. The base must be an ancestor of the head.

**Result.** One line per check, `PASS <check> [<part>]: <details>` or `FAIL ...`, then `gate: passed` or `gate: failed`. With `--log`, the same result as JSON (`base`, `head`, `passed`, and each check's `check`, `part`, `passed`, `details`), for the delivery report to cite. Exit codes: 0 every check passed; 1 at least one check failed; 2 the gate could not run, with every problem on standard error (a missing tool and how to install it, an invalid configuration or profile, a missing design, an unexpected error). Problems are found in stages (the configuration and profiles, then the design, then the tools), and each stage lists every problem it finds. Every check runs even when an earlier one fails, so one run reports everything.

**Inputs.**
- `keyturn/config.json` at the head, checked with `project_config.py check`. Its optional setting `parts` lists each part of the project as `{"path": "<folder>", "profile": "<name>"}`; a folder belongs to one part only, and `"."` stands for the whole repository. The gate stops without it. It is written by `deliver` (#60) once the design is approved, from the design's stack; until then, a person adds it with `project-config`.
- `keyturn/internal/design.md` at the base: the paths in the first column of its "QA's tests" table ([ADR 0017](0017-qa-tests-in-their-own-folder.md)), read at the base so that a change in the range cannot narrow them. A path without a wildcard (`app/qa` or `app/qa/`) protects everything under it. The gate stops without them, or when one is still a template placeholder.
- Each part's profile, `profiles/<name>/profile.json`, a JSON object with exactly these fields:
  - `name`: the profile's folder name;
  - `tools`: `[{"command", "install"}]`, the commands that must be on `PATH`, and how to install each;
  - `setup`: commands to run in the part's folder of each worktree before counting and checking (for example, installing dependencies from the lock file); it may be empty, and a setup that fails fails the part's test count and checks;
  - `checks`: `[{"name", "run"}]`, the commands to run in the part's folder, in order (build, test, lint, and so on), each as a list of words;
  - `count_tests`: a command whose last line of output is the number of tests in the part's folder;
  - `source_files`: file name patterns that the suppression check reads;
  - `suppressions`: regular expressions for suppression comments in those files;
  - `protected`: path patterns of the linter configs and other files no developer change may touch, matched anywhere in the repository (each is read as `**/<pattern>`), since `conventions` puts a config above the part's folder when that folder is one the developer may change.

**Checks, in order.**
1. `protected-paths`: no path that any commit in the range adds, changes, deletes, or renames (both names of a rename) matches a protected pattern. Each commit is compared with each of its parents, so a change that a later commit undoes is still found. The patterns are fixed ones: `keyturn/config.json`, every other role's documents (`keyturn/client/**`, and `keyturn/internal/**` except the developer's `keyturn/internal/handoff.md`), `.github/workflows/**`, and every `.gitattributes` and `.gitignore`, which change what the checks see. Then QA's folders from the design, and each profile's `protected`. In patterns, `**` matches across folders, and `*` and `?` within one name.
2. `suppressions`, per part: no added line in the part's source files matches a suppression pattern (a file outside every part is checked by every profile; the diff is read as text, whatever `.gitattributes` says), unless the same line names `ADR-NNNN`, the project's `keyturn/internal/adr/NNNN-*.md` was accepted at the base, and one of its `- Allows: <text>` lines (in the lines before its first `##` heading, next to its status) gives text that the suppression line contains, such as `//nolint:gosec`. An ADR that allows nothing, or something else, approves nothing; so does an ADR added in the range, which is itself a protected path.
3. `test-count`, per part: the number of tests at the head is not lower than at the base. A part's folder that is not there counts 0, and a count that fails is a failure.
4. Each profile check, per part, at the head.

The profile's commands (`setup`, `checks`, `count_tests`) are the profile's, reviewed in keyturn's own pull requests. A profile should not hand the result to a script the project defines (such as `npm test` running a `package.json` script), since the developer could then change what is run; the profiles (#116, #117) say how each command avoids that, or state the gap.

The gate checks every commit in the range as the developer's. Telling QA's commits apart is decided in #84, within `deliver` (#60), and the gate follows that decision then.

## Reasons

- Python's standard library parses JSON and diffs reliably on macOS and Linux, and keeps the gate testable, as keyturn's other scripts are. `gate.sh` stays the documented entry, as the design names it.
- `keyturn/config.json` is already the file scripts read, and `project-config` already checks it, so the gate reads a checked value instead of parsing prose.
- Exit code 2 separates "the change is wrong" from "the gate could not judge it", so `deliver` sends only the first back to the developer, and a person fixes the second.
- Checking whether the approving ADR was accepted at the base, and protecting the ADR folder, keeps the developer from approving their own suppression in the same change.
- Worktrees of the base and the head check exactly the committed change, and leave the working tree as the developer left it. The cost is a setup (such as installing dependencies) in each worktree on every run.
- Running every check in one go gives the developer the whole list in one round of rework.

## Consequences

- `gates/gate.sh`, `gates/gate.py`, and its tests `gates/test_gate.py` are added. The `go` and `react-spa` profiles (#116, #117) are written in this format.
- `project-config` knows the optional `parts` setting. Projects without it still pass `check`; the gate stops until it is set.
- Not checked yet: skipped or disabled tests, coverage, the scope check against "Areas the work may change", and the security scans (enhancements after the MVP, and phase 5). The delivery report lists what the gate did not check.
- A suppression approved by an ADR leaves the ADR's number in the code, which the review and the delivery report can follow. The project's ADR template has an optional `- Allows:` line for it.
- With every other role's documents protected, the range the gate gets must be the developer's commits only. The state file under `keyturn/internal/state/` is written by `deliver`, and how `deliver` keeps its own commits and QA's out of the range is decided in #60 and #84.
- A profile command runs with the person's environment and network; the sandbox is an enhancement after the MVP (#119).
