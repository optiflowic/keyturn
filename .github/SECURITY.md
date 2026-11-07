# 🔐 Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately through a [GitHub Security Advisory](https://github.com/optiflowic/keyturn/security/advisories/new).
Avoid creating a public issue or pull request.

We will make every effort to respond as quickly as possible and take appropriate action.

## Scope

Please report issues in keyturn itself, for example:

- A way for an agent to bypass a gate or a guardrail (e.g., weakening tests, editing protected paths, skipping security checks)
- A way for untrusted input (issue text, comments, repository content) to make agents act outside the approved task
- Exposure of secrets, tokens, or local files that should never leave the machine

keyturn reduces risk but does not guarantee that the software it builds is free of vulnerabilities. What was and was not verified is listed in each delivery report. Vulnerabilities in software built with keyturn should be reported to that project.

## Supported Versions

keyturn is in early development. Only the latest version on the default branch is supported.

| Version | Supported |
| ------- | --------- |
| latest  | ✅        |

## Notes

- Do **not** disclose security issues publicly until a fix is released.
- For general questions or bug reports, please use the normal issue templates.
