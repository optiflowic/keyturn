---
name: project-config
description: Create or check keyturn's project configuration, keyturn/config.json, which holds the client's language and whether the project uses English-only mode. Use when a keyturn project is being set up, when another keyturn role needs a setting, or when someone asks to see or change the project's language settings. Stops and reports when the file is missing or invalid, instead of guessing a value.
---

# project-config

Create and check the project configuration, `keyturn/config.json`, so that every role reads the same settings and none guesses them. See ADR 0014 in keyturn's `docs/adr/`.

## Rules

- **Never guess a setting.** If the configuration is missing or invalid, stop and report what is wrong. Do not fall back to a default, and do not infer a value from the conversation without asking.
- **Ask the client, then write.** The settings are the client's choices. Ask for them in plain words, and write only what they said.
- **Change the file only on request.** Create it when a project is set up, or change it when the client asks. Every other use is read-only.

## Settings

| Setting | Value | Meaning |
|---|---|---|
| `client_language` | a language code, such as `ja`, `de`, `pt-BR` | The language the client reads and writes. |
| `english_only` | `true` or `false` | `true`: everything committed or posted is in English, and the client reads it through `localize`. `false`: client-facing documents are written in `client_language`. |

There are no other settings yet. A setting is added, with the script and its tests, by the skill that first needs it.

## Inputs

- For creating: the client's language, and whether the project uses English-only mode (for example, a public open-source project whose published content should all be in English).
- For checking or reading: nothing; the file is always `keyturn/config.json` at the repository root.

## Outputs

- `keyturn/config.json`, committed with the other keyturn documents.
- For a check: `ok`, or one line per problem.

## Procedure

The helper script `scripts/project_config.py` (in this skill's folder) does all reading and checking. It needs Python 3.9 or later and Git, and uses only the standard library. Run it from inside the target repository. Below, `project_config.py` means the script's full path.

1. **Check first.** Run `project_config.py check`.
   - `ok`: the configuration can be used. Read a setting with `project_config.py get <setting>`, which checks the file again first.
   - Problems (exit code 1): stop, show the client or the role that asked every line the script printed, and fix the cause before going on. A missing file is created with step 2; any other problem is fixed in step 3.
2. **Create it when the project is set up.** Ask the client which language they read and write, and whether everything published must be in English. Then run `project_config.py init --client-language <code> --english-only` (or `--no-english-only`). The script refuses to overwrite an existing file. Run `check`, and commit the file.
3. **Change it only when the client asks.** Edit `keyturn/config.json` (keep it a JSON object with exactly the settings above), run `check` until it prints `ok`, and commit it. A change of `client_language` or `english_only` changes the language of client-facing documents from then on; tell the client which documents will be written in the new language.

## Notes

- The check always gives the same result for the same file: it lists missing settings, invalid values, and unknown settings, in a fixed order. An unknown setting is an error, so a typo in a setting's name is caught instead of being ignored.
- Scripts and hooks that read the configuration either call `project_config.py get`, or run `project_config.py check` and then parse the JSON themselves.
