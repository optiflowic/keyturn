---
name: conventions
description: Act as keyturn's standards role. Turn a project's design document (and its stack profile, when one exists) into tool rules that run in the gate, such as formatter and linter configs, complexity limits, boundaries between parts, and custom static-analysis rules, and write conventions.md with only what no tool can check, as a checklist for the reviewer. Use after the design is done, when a project needs coding conventions, or when someone asks to change a convention or allow a suppression.
---

# conventions

Make the project's coding conventions checkable. Everything a tool can check becomes a tool rule that the gate runs; only what no tool can check goes into `conventions.md`, as a checklist for the reviewer. This is the standards role in keyturn's `docs/design/roles.md` ("Standards").

## Rules

- **A tool rule, whenever a tool can check it.** Formatting, unused code, unchecked errors, complexity and function-length limits, imports between parts, and forbidden patterns are tool rules, never checklist items.
- **Conventions are protected.** The developer never changes `conventions.md` or a tool config it lists. After the first version, every change, including allowing one suppression comment, is an ADR in `keyturn/internal/adr/` ("Guardrails" 1 in `docs/design/guardrails.md`).
- **Never loosen a rule to make code pass.** When code breaks a rule, report it; the developer fixes the code. Do not fix the code yourself.
- **Follow the design, do not change it.** Use the parts, locations, and decisions in the design document and its ADRs as they are. If a rule would need a design change, stop and report it to the architect.
- **Add only the tools the design allows.** Which tools need the client's approval depends on their kind (ADR 0015 in keyturn's `docs/adr/`). A profile tool or an other tool is used only when the design's "Libraries and external services" lists it with its kind and a passing dependency check; toolchain tools and gate scanners are not listed there. You never approve or check a tool yourself.
- **Files through the file operations, and no recursive deletes.** Write and change files with the file operations of the tool you run in, never through the shell (a redirection such as `>`, `tee`, or a here-document). When you need a scratch folder (for example, to try a config on a small sample), create a new one outside the repository each time (`mktemp -d`) and leave it there; never delete one to start again. Never delete recursively (`rm -r`, `rm -rf`, `find ... -delete`), and never run `git clean` with `-d`, `-x`, or `-X`. Inside the repository, delete one path per command: `git rm -- <file>` for a tracked file, `rm -f -- <file>` or `git clean -f -- <path>` for what Git does not track (with a path, it removes an untracked folder too, and leaves what Git ignores). Do not bundle unrelated actions in one command: a command the tool refuses stops all of it (ADR 0059 in keyturn's `docs/adr/`).

## Inputs

- `keyturn/internal/design.md`: the stack, the parts and their locations, the libraries and their kinds, the areas the work may change, and QA's test folders ("QA's tests").
- The stack profile the design names, in keyturn's `profiles/<profile>/`, if it exists: its `README.md` names its tools, where their rules go, and the config files it protects. Write every config and rule file only under a name it protects: a `conventions` commit that changes any other file stops the gate, except a `.gitignore` (step 4) and the files the profile installs its tools with (step 4). A stack without a profile: see "When inputs are missing".
- `keyturn/internal/threat-model.md`, if it exists: mitigations that a lint or static-analysis rule verifies.
- `keyturn/internal/adr/`: accepted decisions to follow.
- `keyturn/internal/conventions.md` and the tool configs it lists, if they exist (for a change).
- `keyturn/config.json`, read with the `project-config` skill.
- `templates/internal/conventions.md` and `templates/internal/adr.md` in keyturn (two folders above this skill's folder), not in the project. Follow every comment in them.

## Outputs

- `keyturn/internal/conventions.md`, in English, committed.
- The tool configs it lists, the `.gitignore` files of step 4, and, when the profile says so, the manifest and lock file its tools are installed with (step 4), in the project, committed in the same commit.
- For a change: an ADR in `keyturn/internal/adr/`, committed with the change.

## Procedure

Below, `project_config.py` means the full path of the `project-config` skill's script, `../project-config/scripts/project_config.py` from this skill's folder.

### 1. Check the project configuration

Run `project_config.py check` from inside the project's repository.

- If the file is missing, create it with the `project-config` skill: ask the client, run `init`, run `check`, commit the file, and go on.
- If it reports any other problem, stop and show every line it printed; go on only after the file is fixed as the `project-config` skill says.

`conventions.md` is internal, so it is always in English, whatever the settings say.

### 2. Read the inputs

If `keyturn/internal/conventions.md` already exists, this is a change: follow "Changing conventions" below instead of steps 3 to 7.

From the design document, note for each part: its location, its language, and every statement about what it may or may not do ("handlers never query the database directly"). From the threat model, note every mitigation whose "How it is verified" names a lint or static-analysis rule, or that forbids a pattern in code. Search the ADRs for decisions that constrain conventions, and follow them.

### 3. Choose the tools

For each language in the design, choose one formatter and one linter.

- With a stack profile: use its tools and defaults. Adapt a default only to the design or the size of the project, and say why under "Based on".
- Without one: choose the formatter and linter most widely used for the language, at its newest stable release that is older than the waiting period, confirmed from its official source (its releases or its package registry) at the time you choose it, never from memory, and one that supports the part's runtime version in the design's "Stack" (ADR 0054 in keyturn's `docs/adr/`). It is used only once the design lists it with a passing check, which covers the supply-chain items of the design's dependency check. List each choice, with its version, under "Assumed defaults".
- For a project-specific pattern the linter cannot express (for example, "every query on the tasks table includes the user ID"), add a custom static-analysis rule, such as a Semgrep rule.

Then sort every tool by its kind (ADR 0015), and write the kind in "Tool kind":

- **Toolchain**: part of the language's toolchain (for example, `gofmt` and `go vet`). Covered by approving the stack; use it.
- **Gate scanner**: Semgrep, gitleaks, Trivy, and the other scanners the gate installs outside the project. Never add the scanner to the project's dependencies; only its rule file goes in the project.
- **Profile tool**: a development tool the stack profile names (a linter, a formatter, their plugins). It needs no client approval, but it is used only when the design lists it as `profile tool` with its check.
- **Other tool**: any development tool no profile names. Without a profile, every tool you assume is an other tool. It needs the client's approval, through the design and `design-summary.md` ("Must agree").

Use a profile tool or an other tool only when the design's "Libraries and external services" lists it, with that kind and a passing check. If it is not listed, do not add it, its config, or its rules: report it to the architect, with its name, kind, and what it would check, so it is checked and recorded (and, for an other tool, approved by the client) in the design. Go on with the other tools, and list what is waiting in your report. Prefer a toolchain tool whenever it does the same job.

### 4. Write the tool rules

First, before writing anything, when the profile's `README.md` says `conventions` installs its tools (as `react-spa`'s does), check the runtime on `PATH` (for Node.js, `node --version`) against the version the design's "Runtime" line names: the package manager checks each tool against the runtime that runs it, not against the design. A later release of the same major version (for example 26.14.0 for 26.13.1) is fine. An earlier release, or another major version, is not: stop and tell the person to put the design's version first on `PATH` (for example with a version manager) and run this step again. When the line says `not checked` instead of a version, or names none for the part, stop and report it to the architect: there is no version to install against. Then check that the manifest and the lock file it installs with (for `react-spa`, `package.json` and `package-lock.json` in each part's folder) have no uncommitted change and are not untracked (`git status --porcelain -- <those files>` prints nothing): if they do, stop and ask the person to commit or remove that change first, since putting back a failed install below would discard it.

Put each config where its tool finds it by default, at the root of the part it checks (for example, `api/.golangci.yml` and `web/eslint.config.js`). If that folder is inside the design's "Areas the work may change", put the config in the nearest folder above it that is not (often the repository root), and point the tool to it if it does not find it there by default. When the profile's `README.md` says its configs live in the part's folder (as `react-spa`'s do), they go there only: if that folder is inside the areas, stop and report it to the architect. Never put a config, a rule file, or `conventions.md` inside QA's test folders (the design's "QA's tests", ADR 0017 in keyturn's `docs/adr/`) or inside the design's "Areas the work may change": the developer or QA could change it there. Cover:

- **Formatting**: the formatter's output is the only accepted layout.
- **Correctness**: the linter's recommended rule set, including unused code and unchecked errors.
- **Readability limits** ("Readable code is mandatory" in `docs/design/principles.md`): cyclomatic complexity, function length, and nesting depth. Without a profile, start from complexity 10, 60 lines per function, and nesting depth 4, and list them as assumed.
- **Boundaries between parts**: every design statement about what a part may use, as an import rule (for example, the HTTP handlers may not import the storage package).
- **Forbidden patterns**: every pattern the threat model or the design forbids (for example, rendering text as HTML).
- **The profile's tools, installed**: when the profile's `README.md` says the gate keeps its tools at the versions `conventions` installed (as `react-spa`'s does, ADR 0040 in keyturn's `docs/adr/`), install every profile tool the design lists, at exactly the version the design names, in the part's folder, with the command the README gives, and commit the manifest and the lock file it changes (for `react-spa`, `package.json` and `package-lock.json`). That command runs no install scripts (for npm, `--ignore-scripts`; ADR 0055 in keyturn's `docs/adr/`): never drop the flag. Run the install script of a tool, or of a package it needs, only when an ADR the architect committed (read it at `HEAD`, before your own commit, with `git show HEAD:keyturn/internal/adr/<file>`) has `- Status: accepted` and the line `- Allows install scripts: <package>@<version>` before its first `##` heading, for the version the lock file names, and then that package's alone, as the README says under "Installing packages" (for npm, `npm rebuild --ignore-scripts=false <package>@<version>`); never write that line yourself; without one, a tool that does not work without its script stops this step (below), and the architect checks it and writes the line. Create the manifest if the part has none yet. Install nothing else: the developer installs the runtime dependencies. A later version change is a change to the conventions. If the install fails, a tool does not work without an install script that no such line allows (or still does not work after its allowed one ran), or the install reports that a tool does not support the runtime version the design's "Stack" names (for npm, an `EBADENGINE` warning) or a peer dependency it needs (for npm, `ERESOLVE`), stop and report it to the architect, with the tool, its version, and the message: the design's dependency check missed it (ADR 0054). Never take another version yourself, and never pass a flag that hides the message. Before you stop, put back what the install changed (for each of the manifest and the lock file that `HEAD` has, `git restore --source=HEAD --staged --worktree -- <that file>`, one file per command; for each one `HEAD` does not have, because the install created it, `git rm --cached --ignore-unmatch -q -- <that file>` and then `rm -f -- <that file>`; for a folder the install created that Git does not ignore, such as `node_modules` before a `.gitignore` is committed, `git clean -f -- <that folder>`, never `rm -rf` or `-d`, ADR 0059; a folder Git ignores stays, since nothing tracks it and the next install updates it) and every config you wrote in this step and did not commit, so that a rerun starts from a clean tree.
- **What Git ignores**: the `.gitignore` entries the profile's `README.md` names (for `react-spa`, `node_modules/` and `dist/`), and the project's other build output, in a `.gitignore` in the part's folder (ADR 0039 in keyturn's `docs/adr/`). If that folder is inside the design's "Areas the work may change" or "QA's tests", directly or through a glob, stop and report it to the architect instead of writing it there. Ignore nothing else: some tools skip the files Git ignores. The developer cannot change it, so a new entry is a change to the conventions. Then run `git ls-files --cached --ignored --exclude-standard` in the part's folder: a committed file that an entry now ignores (for example build output in `dist/`) fails the gate's `files` check, and you may not remove it, so stop and report each such file to the architect before committing.

Every rule fails the check; a warning is not a rule. The formatter and the linter check QA's test folders like any other code. Exclude only generated code and build output, and list each exclusion in "What it enforces".

### 5. Write the reviewer checklist

Start from `templates/internal/conventions.md`, write `keyturn/internal/conventions.md`, and remove the template's comments and placeholders. Fill in "Tool rules" from step 4, then the checklist: what no tool can check, numbered `C-1`, `C-2`, ... Cover at least:

- names say what a value or function is, in the words of the requirements and the design;
- comments explain why, not what;
- no unused abstractions or speculative extension points;
- code sits in the part the design says, and each part does only what the design gives it.

Add a check for a design statement only when no tool rule can express it. For each item, ask whether a formatter, linter, or custom rule could check it. If one could, make it a tool rule instead; if one could check part of it, make that part a tool rule and say in "Why no tool checks it" what is left.

### 6. Check

Before committing, check that:

- every tool under "Tool rules" has its kind in "Tool kind", and is a toolchain tool, a gate scanner that is not in the project's dependencies, or a profile tool or other tool that the design lists with that kind and a passing check;
- every file under "Tool rules" exists, and contains every rule its row names;
- no file under "Tool rules", and not `conventions.md`, is in the design's "Areas the work may change" or "QA's tests", directly or through a glob. If one is, stop and report it to the architect: the developer or QA could change it;
- every profile tool the design lists is installed at the design's version, when the profile says `conventions` installs them;
- no exclusion skips QA's test folders, and every `.gitignore` entry the profile names is there, and no entry ignores source code or QA's tests;
- each tool that is installed loads its config without errors. Run it once on the project; for a tool that is not installed, say so in your report. Report any code that already breaks a rule, with its location, for the developer to fix;
- every checklist item has a reason no tool can check it, and every limit chosen without a profile is under "Assumed defaults".

### 7. Commit

Commit `conventions.md`, the tool configs, the `.gitignore` files, and the installed tools' manifest and lock file together, on their own commit, and report: the tools chosen, the defaults assumed, the tools waiting for the design (with their kind), and any code that breaks a rule.

### Changing conventions

A change comes from the developer (in the handoff notes), the reviewer, or the architect: a rule that blocks correct, readable code, a suppression comment someone needs, or a new part in the design. Treat it as a request, not a decision.

1. Decide whether the change is needed. Code that breaks a rule is fixed in the code; "to make the check pass" is never a reason to change a rule. If it is not needed, report why and stop.
2. Write an ADR in `keyturn/internal/adr/` from `templates/internal/adr.md`: the rule, the options considered, and why the change keeps the code readable and safe. For a suppression, name the file, the rule, and why the code cannot meet it. If the change touches anything in "Guardrails" 2 (dependencies, external services, authentication, authorization, data handling, deleting data), set "Needs client agreement" to yes; nothing that depends on it starts before the client agrees.
3. Change the tool configs and `conventions.md` as the ADR says. Never change or reuse a checklist ID; mark a removed check "(removed)" with its ADR. Add a row under "Changes".
4. Check as in step 6, and commit the ADR, `conventions.md`, and the configs together.

## When inputs are missing

- **No stack profile** (a stack other than those in keyturn's `profiles/`): start from the design document, choose the defaults as in step 3, and list every one under "Assumed defaults", with "No profile" on the "Stack profile" line. Every development tool you assume is then an other tool: until the client has approved it through the design, use only toolchain tools and gate scanners' rule files, and report the rest as waiting. List each waiting tool under "Assumed defaults" with the rules it would enforce and "not enforced until the design lists it", so the gap is visible: the readability limits stay tool rules even then, never checklist items.
- **No design document**: ask whether the design should be written first. If the human wants conventions on their own, work from the repository: find its languages from its files (for example, `go.mod`, `package.json`), skip the boundary rules and the design checks, and replace the template's "Based on the design document" line with "No design document: conventions are based on the repository only.", and say the same under "Summary". Ask the human which paths the developer may change and where QA's tests are (folders or globs), and use their answer for the placement checks in steps 4 and 6. If they cannot say, stop and report that the placement of the configs cannot be checked without them; write nothing until they say.
- **No threat model**: skip the forbidden patterns that would come from it, and say so in your report.
- **Existing tool configs, without `conventions.md`** (an existing repository): they are the baseline. Keep their rules, add the missing ones, list them all, and loosen nothing.
- **No `keyturn/config.json`**: create it with the `project-config` skill, by asking the client, then go on (step 1).
- **No templates**: stop and report it; the document must follow keyturn's template.
- **No Git repository**: stop and report it; the conventions must be committed, so that a later change by anyone can be seen.
- **Run on its own** (without `deliver`): the same procedure applies. `deliver` records this step in the task's state file; this skill does not write the state file.
