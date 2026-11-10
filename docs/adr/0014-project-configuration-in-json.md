# 0014. The project configuration is a JSON file, checked by a script before use

- Status: accepted
- Date: 2026-11-10

## Context

"Projects that use keyturn" in `docs/DESIGN.md` says that the language settings are stored per project in keyturn's project configuration, but not where or in what format (#68). The `spec` skill (#53) is the first skill that runs in a project, and it needs two settings: the client's language, and whether the project uses English-only mode.

Later, the configuration will also hold settings that scripts and hooks read without an agent in between: for example, the usage-limit thresholds that a hook checks before every tool call (#62). So the format has to work for two kinds of reader:

- **People**, who set it up once, look at it now and then, and sometimes edit it by hand.
- **Scripts and hooks**, which read it often, sometimes from a shell, and must never guess a value.

Only the two settings used now are defined here. Each later setting is added by the skill or adapter that uses it.

## Options considered

1. **Markdown with fixed fields** (`- Field: value` lines), like the task state file (ADR 0011).
   - People: the easiest to read, and it can carry a sentence explaining each setting.
   - Scripts: there is no standard parser, so every reader needs keyturn's own parsing rules (spacing, case, how `true` is written), and a shell hook would have to call a Python helper to read one value. Values are all text, so a typo such as `ture` is only caught if every reader checks for it.
2. **JSON** (`keyturn/config.json`).
   - People: readable for a handful of settings, but it has no comments, and a missing comma or quote breaks the whole file.
   - Scripts: every language has a standard parser (Python's `json`, `jq` in a shell), true and false are real booleans, and a broken file fails to parse instead of being read wrongly.
3. **TOML**: readable and allows comments, but Python only reads it from 3.11 (keyturn's scripts support 3.9), and shells have no common reader.

## Decision

Option 2. The project configuration is `keyturn/config.json`, a JSON object with exactly these settings for now:

```json
{
  "client_language": "ja",
  "english_only": false
}
```

- `client_language`: the language the client reads and writes, as a language code (`ja`, `de`, `pt-BR`), the same form `localize` accepts.
- `english_only`: `true` when the project uses English-only mode (everything committed or posted is in English, and the client reads it through `localize`); `false` when client-facing documents are written in the client's language.

The file is created and checked by the `project-config` skill, with its helper script `skills/project-config/scripts/project_config.py`:

- `check` reports whether the file is valid: it exists, it is UTF-8 JSON, it is an object with every required setting, every value has the right type and form, and there is no setting it does not know. It lists every problem, always in the same order, so the same file always gives the same result.
- Every skill, script, or hook that reads the configuration runs `check` first (or reads it through the script) and stops if it fails, saying what is wrong. Nothing guesses a missing or broken value, and nothing falls back to a default.
- A setting added later is added to the script and its tests in the same pull request, so `check` keeps knowing every setting.

## Reasons

- The settings that matter most for safety, such as usage-limit thresholds, are read by hooks without an agent to notice a mistake, so reliable parsing matters more than prose.
- A JSON parser rejects a broken file outright, and booleans and numbers keep their type, so the check only has to cover what the parser cannot.
- With two settings, and only a few more later, the file stays short enough to read without comments; the skill explains each setting where people look for it.
- This differs from the task state file (ADR 0011) on purpose: that file is read mostly by people and by one skill, and it changes at every step; this one changes rarely and is read by many scripts.

## Consequences

- A new `project-config` skill creates the file with the client and checks it; the plugin version is bumped.
- The `spec` skill (#53) runs the check before anything else and writes client-facing documents in `client_language` unless `english_only` is true.
- Hooks and adapters (#62) read the file through the script, or with a JSON parser after running `check`.
- People editing the file by hand can break it with a stray comma; `check` then stops every skill until it is fixed, and says where the parser failed.
- The worked example has a `keyturn/config.json`.
