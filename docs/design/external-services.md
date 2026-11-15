# External Services

By default, keyturn sends code and documents nowhere except to the AI tool the client already uses (Claude Code or Codex, under whatever plan or contract the client has).

- Gates run locally (e.g., Semgrep, gitleaks, Trivy run on the machine or in CI).
- Some checks need public data, such as vulnerability databases (e.g., OSV). These send only package names and versions, never code.
- Translation (`localize`) is done by the AI tool itself. No translation service is used.
- Any other external service (e.g., hosted scanners, cloud rule registries) is opt-in, off by default, and listed in the README with exactly what it sends.
