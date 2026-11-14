# Pre-pull-request checklist

What the review before a pull request checks ([ADR 0019](adr/0019-pre-pull-request-review.md)). Each section names the paths it applies to; the reviewer gets only the sections that match the changed paths. Where a rule is already stated in `AGENTS.md`, `docs/DESIGN.md`, or an ADR, the item links to it instead of repeating it.

## Every change

- [ ] Every link in the diff to a file in this repository points to a file that exists on `main` or in this pull request, not to a file that only an unmerged pull request adds.
- [ ] A claim that uses "every", "all", "never", "only", or "always" has no counterexample. Look for one before accepting the claim.
- [ ] A definition holds for every case it covers, such as every stack or tool it names, not only the first one that comes to mind.

## Documents: `docs/**`, `AGENTS.md`, `templates/**`, `evals/**`, `.github/**`

- [ ] A changed rule or statement says the same as every other place that states it: `docs/DESIGN.md`, the ADRs, `AGENTS.md`, the templates, the worked examples, the skills, and what the scripts do.
- [ ] After a line was changed, the other lines in the same file that depend on it (a recommendation, a summary, an example) still agree with it.
- [ ] Nothing presents a `proposed` ADR as decided ([ADR rules](adr/README.md)).
- [ ] A worked example fills in every part its template asks for, and a template change has its example updated ("Before opening a pull request" in [`AGENTS.md`](../AGENTS.md)).
- [ ] A procedure in "Trying changes locally" in [`AGENTS.md`](../AGENTS.md), followed step by step as written, reaches the state it is meant to try (for example, a file is committed before a step that reads the committed file).

## Skills: `skills/**/SKILL.md`

- [ ] If the work stops after any step and is started again, nothing is recorded twice, nothing is lost, and every check the skill runs still passes on what was already recorded, such as a decision the client has since agreed to ([Resuming Work](DESIGN.md#resuming-work)).
- [ ] Every way an answer can come in (for example, an answer to a card that stands for agreeing to a decision) moves each status it affects, and none is left waiting.
- [ ] The skill says what to do when an input is missing ([Roles are usable on their own](DESIGN.md#roles-are-usable-on-their-own)), and when the repository is in a state it did not create, such as another branch or files committed before keyturn.
- [ ] The client's words that change what will be built are not committed or recorded before their English is confirmed ([ADR 0013](adr/0013-confirming-translations-into-english.md)).
- [ ] Every skill, script, or file the skill relies on exists on `main` or in this pull request.

## Scripts and their tests: `skills/**/scripts/**`, `scripts/**`

- [ ] An unexpected error (for example, `OSError` when a file cannot be written) ends with a clear message, not a traceback, and a failure never reports success.
- [ ] The exit code of every subprocess is checked.
- [ ] Environment variables (such as `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`), symbolic links, and a file where a folder is expected cannot make the script read or write somewhere else.
- [ ] Every free-form value read from a file is checked against the values it may take, and fields that contradict each other are rejected.
- [ ] A response from an external service is checked for errors before its data is used, and a result with a size limit is fetched page by page.
- [ ] The tests do not depend on the operating system (line endings, paths) or on the developer's setup (global Git configuration, `GIT_*` variables).
- [ ] The tests cover the edge cases the change handles.

## The plugin: `skills/**`, `templates/**`, `.claude-plugin/**`

- [ ] The pull request follows the version rule for `.claude-plugin/` in "Where things live" in [`AGENTS.md`](../AGENTS.md).
