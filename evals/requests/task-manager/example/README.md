# Worked example: task manager

Every keyturn template, filled in by hand for [the task manager request](../request.md), as the roles would fill them in. Later skills and evaluations can compare their output with it.

- Nothing was built. The commits, test names, results, findings, and tool versions are illustrative: they show what each document should contain, not the result of a real run.
- Versions and vulnerability IDs are made up or left out. Versions of real libraries and tools are not written down, because they go out of date; the documents say where the version is pinned instead (for example, `api/go.mod` or `web/package.json`). Vulnerability IDs, such as `GO-0000-0001`, are made up, so they cannot be mistaken for real advisories.
- The example is public, so everything is in English, including the client-facing documents (as in a project in English-only mode). The client read the requirements in a local Japanese translation made with `localize`; the translation itself is not committed.
- The folders mirror a project that uses keyturn: `keyturn/client/` for the client, `keyturn/internal/` for the roles.
- It shows the project at the end of delivery 1. The work was split into two deliveries so that each acceptance guide has no more than five "Must check" items: delivery 1 covers R-1 to R-4, R-7, and R-8; delivery 2 (not shown) covers R-5, R-6, and R-9.

## Documents

| Document | Template | Filled in by |
|---|---|---|
| [`keyturn/client/requirements.md`](keyturn/client/requirements.md) | `templates/client/requirements.md` | PM |
| [`keyturn/client/approvals.md`](keyturn/client/approvals.md) | `templates/client/approvals.md` | PM |
| [`keyturn/client/decision-card-1.md`](keyturn/client/decision-card-1.md) | `templates/client/decision-card.md` | Architect |
| [`keyturn/client/design-summary.md`](keyturn/client/design-summary.md) | `templates/client/design-summary.md` | Architect |
| [`keyturn/client/acceptance-guide.md`](keyturn/client/acceptance-guide.md) | `templates/client/acceptance-guide.md` | PM |
| [`keyturn/client/delivery-report.md`](keyturn/client/delivery-report.md) | `templates/client/delivery-report.md` | PM |
| [`keyturn/internal/design.md`](keyturn/internal/design.md) | `templates/internal/design.md` | Architect |
| [`keyturn/internal/threat-model.md`](keyturn/internal/threat-model.md) | `templates/internal/threat-model.md` | Architect |
| [`keyturn/internal/adr/`](keyturn/internal/adr/) | `templates/internal/adr.md` | Architect |
| [`keyturn/internal/handoff.md`](keyturn/internal/handoff.md) | `templates/internal/handoff.md` | Developer |
| [`keyturn/internal/test-report.md`](keyturn/internal/test-report.md) | `templates/internal/test-report.md` | QA |
| [`keyturn/internal/review.md`](keyturn/internal/review.md) | `templates/internal/review.md` | Reviewer |
| [`keyturn/internal/security-review.md`](keyturn/internal/security-review.md) | `templates/internal/review.md` | Security |

## Checking the approval record

[`approvals.md`](keyturn/client/approvals.md) records two hashes, taken when version 1 was sent: the SHA-256 of `requirements.md` (also the `sha256` on the first line of the Japanese translation), and the SHA-256 of the translation file the client read. The translation is kept only locally, so only the first one can be checked from this repository. To check that the approval is still current, from the repository root:

```sh
shasum -a 256 evals/requests/task-manager/example/keyturn/client/requirements.md
```

If the result differs from the row in `approvals.md`, the requirements changed after the approval, and the approval is stale.
