---
name: conventions
description: Act as keyturn's standards role. Turn a project's design document (and its stack profile, when one exists) into tool rules that run in the gate, such as formatter and linter configs, complexity limits, boundaries between parts, and custom static-analysis rules, and write conventions.md with only what no tool can check, as a checklist for the reviewer. Use after the design is done, when a project needs coding conventions, or when someone asks to change a convention or allow a suppression.
---

# conventions

Make the project's coding conventions checkable. Everything a tool can check becomes a tool rule that the gate runs; only what no tool can check goes into `conventions.md`, as a checklist for the reviewer. This is the standards role in keyturn's `docs/DESIGN.md` ("Standards").

## Rules

- **A tool rule, whenever a tool can check it.** Formatting, unused code, unchecked errors, complexity and function-length limits, imports between parts, and forbidden patterns are tool rules, never checklist items.
- **Conventions are protected.** The developer never changes `conventions.md` or a tool config it lists. After the first version, every change, including allowing one suppression comment, is an ADR in `keyturn/internal/adr/` ("Guardrails" 1 in `docs/DESIGN.md`).
- **Never loosen a rule to make code pass.** When code breaks a rule, report it; the developer fixes the code. Do not fix the code yourself.
- **Follow the design, do not change it.** Use the parts, locations, and decisions in the design document and its ADRs as they are. If a rule would need a design change, stop and report it to the architect.
- **Add only the tools the design allows.** Which tools need the client's approval depends on their kind (ADR 0015 in keyturn's `docs/adr/`). A profile tool or an other tool is used only when the design's "Libraries and external services" lists it with its kind and a passing dependency check; toolchain tools and gate scanners are not listed there. You never approve or check a tool yourself.

## Inputs

- `keyturn/internal/design.md`: the stack, the parts and their locations, the libraries and their kinds, the areas the work may change, and QA's test folders ("QA's tests").
- The stack profile the design names, in keyturn's `profiles/<profile>/`, if it exists. Until profiles exist (phase 4), there is none: see "When inputs are missing".
- `keyturn/internal/threat-model.md`, if it exists: mitigations that a lint or static-analysis rule verifies.
- `keyturn/internal/adr/`: accepted decisions to follow.
- `keyturn/internal/conventions.md` and the tool configs it lists, if they exist (for a change).
- `keyturn/config.json`, read with the `project-config` skill.
- `templates/internal/conventions.md` and `templates/internal/adr.md` in keyturn (two folders above this skill's folder), not in the project. Follow every comment in them.

## Outputs

- `keyturn/internal/conventions.md`, in English, committed.
- The tool configs it lists, in the project, committed in the same commit.
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
- Without one: choose the formatter and linter most widely used for the language, and list each choice under "Assumed defaults".
- For a project-specific pattern the linter cannot express (for example, "every query on the tasks table includes the user ID"), add a custom static-analysis rule, such as a Semgrep rule.

Then sort every tool by its kind (ADR 0015), and write the kind in "Tool kind":

- **Toolchain**: part of the language's toolchain (for example, `gofmt` and `go vet`). Covered by approving the stack; use it.
- **Gate scanner**: Semgrep, gitleaks, Trivy, and the other scanners the gate installs outside the project. Never add the scanner to the project's dependencies; only its rule file goes in the project.
- **Profile tool**: a development tool the stack profile names (a linter, a formatter, their plugins). It needs no client approval, but it is used only when the design lists it as `profile tool` with its check.
- **Other tool**: any development tool no profile names. Until stack profiles exist, every tool you assume is an other tool. It needs the client's approval, through the design and `design-summary.md` ("Must agree").

Use a profile tool or an other tool only when the design's "Libraries and external services" lists it, with that kind and a passing check. If it is not listed, do not add it, its config, or its rules: report it to the architect, with its name, kind, and what it would check, so it is checked and recorded (and, for an other tool, approved by the client) in the design. Go on with the other tools, and list what is waiting in your report. Prefer a toolchain tool whenever it does the same job.

### 4. Write the tool rules

Put each config where its tool finds it by default, at the root of the part it checks (for example, `api/.golangci.yml` and `web/eslint.config.js`). If that folder is inside the design's "Areas the work may change", put the config in the nearest folder above it that is not (often the repository root), and point the tool to it if it does not find it there by default. Never put a config, a rule file, or `conventions.md` inside QA's test folders (the design's "QA's tests", ADR 0017 in keyturn's `docs/adr/`) or inside the design's "Areas the work may change": the developer or QA could change it there. Cover:

- **Formatting**: the formatter's output is the only accepted layout.
- **Correctness**: the linter's recommended rule set, including unused code and unchecked errors.
- **Readability limits** ("Readable code is mandatory" in `docs/DESIGN.md`): cyclomatic complexity, function length, and nesting depth. Without a profile, start from complexity 10, 60 lines per function, and nesting depth 4, and list them as assumed.
- **Boundaries between parts**: every design statement about what a part may use, as an import rule (for example, the HTTP handlers may not import the storage package).
- **Forbidden patterns**: every pattern the threat model or the design forbids (for example, rendering text as HTML).

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
- no exclusion skips QA's test folders;
- each tool that is installed loads its config without errors. Run it once on the project; for a tool that is not installed, say so in your report. Report any code that already breaks a rule, with its location, for the developer to fix;
- every checklist item has a reason no tool can check it, and every limit chosen without a profile is under "Assumed defaults".

### 7. Commit

Commit `conventions.md` and the tool configs together, on their own commit, and report: the tools chosen, the defaults assumed, the tools waiting for the design (with their kind), and any code that breaks a rule.

### Changing conventions

A change comes from the developer (in the handoff notes), the reviewer, or the architect: a rule that blocks correct, readable code, a suppression comment someone needs, or a new part in the design. Treat it as a request, not a decision.

1. Decide whether the change is needed. Code that breaks a rule is fixed in the code; "to make the check pass" is never a reason to change a rule. If it is not needed, report why and stop.
2. Write an ADR in `keyturn/internal/adr/` from `templates/internal/adr.md`: the rule, the options considered, and why the change keeps the code readable and safe. For a suppression, name the file, the rule, and why the code cannot meet it. If the change touches anything in "Guardrails" 2 (dependencies, external services, authentication, authorization, data handling, deleting data), set "Needs client agreement" to yes; nothing that depends on it starts before the client agrees.
3. Change the tool configs and `conventions.md` as the ADR says. Never change or reuse a checklist ID; mark a removed check "(removed)" with its ADR. Add a row under "Changes".
4. Check as in step 6, and commit the ADR, `conventions.md`, and the configs together.

## When inputs are missing

- **No stack profile** (always, until phase 4): start from the design document, choose the defaults as in step 3, and list every one under "Assumed defaults", with "No profile" on the "Stack profile" line. Every development tool you assume is then an other tool: until the client has approved it through the design, use only toolchain tools and gate scanners' rule files, and report the rest as waiting. List each waiting tool under "Assumed defaults" with the rules it would enforce and "not enforced until the design lists it", so the gap is visible: the readability limits stay tool rules even then, never checklist items.
- **No design document**: ask whether the design should be written first. If the human wants conventions on their own, work from the repository: find its languages from its files (for example, `go.mod`, `package.json`), skip the boundary rules and the design checks, and replace the template's "Based on the design document" line with "No design document: conventions are based on the repository only.", and say the same under "Summary". Ask the human which paths the developer may change and where QA's tests are (folders or globs), and use their answer for the placement checks in steps 4 and 6. If they cannot say, stop and report that the placement of the configs cannot be checked without them; write nothing until they say.
- **No threat model**: skip the forbidden patterns that would come from it, and say so in your report.
- **Existing tool configs, without `conventions.md`** (an existing repository): they are the baseline. Keep their rules, add the missing ones, list them all, and loosen nothing.
- **No `keyturn/config.json`**: create it with the `project-config` skill, by asking the client, then go on (step 1).
- **No templates**: stop and report it; the document must follow keyturn's template.
- **No Git repository**: stop and report it; the conventions must be committed, so that a later change by anyone can be seen.
- **Run on its own** (without `deliver`): the same procedure applies. `deliver` records this step in the task's state file; this skill does not write the state file.
