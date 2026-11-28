# Pre-pull-request checklist

What the review before a pull request checks ([ADR 0019](adr/0019-pre-pull-request-review.md)). Each section names the paths it applies to; the reviewer gets only the sections that match the changed paths. Where a rule is already stated in `AGENTS.md`, the design (`docs/design/`), or an ADR, the item links to it instead of repeating it.

## Every change

- [ ] Every link in the diff to a file in this repository points to a file that exists on `main` or in this pull request, not to a file that only an unmerged pull request adds.
- [ ] A claim that uses "every", "all", "never", "only", or "always" has no counterexample. Look for one before accepting the claim.
- [ ] Every skill, script, or file that the change relies on, and every caller it says runs something (for example, "the `deliver` skill runs this"), exists on `main` or in this pull request; otherwise the change says what does not happen yet.
- [ ] A path one context hands to another (a skill to a subagent, a step to a role) resolves in the context that receives it: a path relative to a skill's folder is given as a full path to a context that has no such folder.
- [ ] A rule fixes the way of working, not a tool: a skill, a template, an ADR, or the design names no specific development tool, library, or service as the rule (for example, "QA tests in a real browser with the E2E tool the stack profile names", never a named test tool), and says where the tool is chosen (a stack profile, as its current choice, or a project's design, with the client). Only a stack profile names its tools, and a worked example names those of its own stack ([Stack Profiles](design/stack-profiles.md)).
- [ ] A definition, or a list of the values something may take, holds for every case it covers, such as every stack or tool it names, every state a rule allows, or every kind of change a rule about changed files covers (a deleted or renamed file too), not only the first one that comes to mind.

## Documents: `docs/**`, `AGENTS.md`, `templates/**`, `evals/**`, `.github/**`

- [ ] A changed rule or statement says the same as every other place that states it: the design (`docs/design/`, and its index, `docs/DESIGN.md`, for headings), the ADRs, `AGENTS.md`, the templates (including the issue forms and the pull request template), the worked examples, the skills, and what the scripts do.
- [ ] After a line was changed, the other lines in the same file that depend on it (a recommendation, a summary, an example) still agree with it. A new exception to a rule is also stated, or pointed to, wherever another section, or another skill or template, restates that rule (for example, a rule the design template states and the review skill checks).
- [ ] Nothing presents a `proposed` ADR as decided ([ADR rules](adr/README.md)).
- [ ] A worked example fills in every part its template asks for, and a template change has its example updated ("Before opening a pull request" in [`AGENTS.md`](../AGENTS.md)).
- [ ] When a client document of a worked example changed, every hash `approvals.md` records for the version or delivery the example now holds changed too: the source SHA-256 to the file's, and the translation SHA-256 to a new value, since a translation of the old text cannot match the new one. Rows of earlier versions keep their hashes.
- [ ] A procedure in [`docs/trying-locally.md`](trying-locally.md), followed step by step as written, reaches the state it is meant to try (for example, a file is committed before a step that reads the committed file), and every check it asks for passes on a correct run, including the exceptions the skill allows and what the procedure's own earlier steps leave behind (for example, a branch a script it runs pushed).

## Skills: `skills/**/SKILL.md`

- [ ] If the work stops after any step and is started again, nothing is recorded twice, nothing is lost, every command still works on what was already recorded (a `git commit` of a file that is already committed has nothing to commit, and fails), and every check the skill runs still passes on what was already recorded, such as a decision the client has since agreed to ([Resuming Work](design/resuming-work.md)).
- [ ] Every way an answer can come in (for example, an answer to a card that stands for agreeing to a decision) moves each status it affects, and none is left waiting.
- [ ] The skill says what to do when an input is missing ([Roles are usable on their own](design/roles.md#roles-are-usable-on-their-own)), and when the repository is in a state it did not create, such as another branch or files committed before keyturn.
- [ ] A skill that works on a Git range reads the code at the range's head and the documents it judges the code by as they were before the range (at its base), never from a checkout at another commit; a change to those documents inside the range is a finding, found commit by commit, so that a change a later commit undoes is found too; and scripts that read the working tree run only on a checkout where those documents are as they were at the base.
- [ ] The client's words that change what will be built are not committed or recorded before their English is confirmed ([ADR 0013](adr/0013-confirming-translations-into-english.md)).
- [ ] Walk through the procedure step by step, as written, in three cases: the first run, in a repository that has none of the skill's outputs yet; each input missing, one at a time; and a rerun. Every step can be done as written and leaves what the next step expects, and on a rerun, a step that judges a result judges one from this run, on the current commit, never one an earlier run left; the other items in this section say what to check in each case.
- [ ] Every command the skill gives works in each case the skill allows, and does all it is meant to (for example, `git restore` without `--staged` leaves a staged change in place): the first run (for example, a new file is not yet tracked, so it must be added before `git commit -- <path>`), and each missing input.
- [ ] The skill allows nothing that the [Guardrails](design/guardrails.md) forbid or make wait for the client: what always needs the client's approval, even when a document lists it, and what fails the gate (such as a drop in the number of tests).

## Scripts and their tests: `skills/**/scripts/**`, `scripts/**`, `gates/**`, `github/scripts/**`

- [ ] An unexpected error (for example, `OSError` when a file cannot be written) ends with a clear message, not a traceback, and a failure never reports success.
- [ ] The exit code of every subprocess is checked.
- [ ] Environment variables (such as `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`), symbolic links, and a file where a folder is expected cannot make the script read or write somewhere else.
- [ ] Every free-form value read from a file is checked against the values it may take, and fields that contradict each other are rejected. A record that cannot be read in full (a missing heading, a row with too few cells, an indented heading, a line inside a comment or a code block) fails the check instead of being skipped or read as empty.
- [ ] A response from an external service is checked for errors before its data is used, and a result with a size limit is fetched page by page.
- [ ] The tests do not depend on the operating system (line endings, paths) or on the developer's setup (global Git configuration, `GIT_*` variables).
- [ ] The tests cover the edge cases the change handles.

## The plugin: `skills/**`, `templates/**`, `.claude-plugin/**`

- [ ] The pull request follows the version rule for `.claude-plugin/` in "Where things live" in [`AGENTS.md`](../AGENTS.md).
