# 0003. Password sign-in with sessions stored on the server

- Status: accepted
- Date: 2026-11-08
- Serves: R-1, R-2, R-7, R-8
- Needs client agreement: yes

## Context

People sign up and sign in with a username and a password (R-1, R-2), and every request must be tied to one person so that tasks stay private (R-7). This is a change to authentication, which always needs the client's approval. Passwords must be stored so that a stolen database makes them as slow to guess as possible.

## Options considered

1. **Sessions stored on the server, in a cookie that scripts cannot read; passwords hashed with Argon2id from `golang.org/x/crypto`**: signing out ends the session at once, and the cookie cannot be read by code in the page. Argon2id is the current recommendation for password storage. One new dependency, maintained by the Go team.
2. **Signed tokens kept in the browser (JWT)**: no session table, but signing out cannot end a token before it expires, and tokens kept where scripts can read them can be stolen by injected code.
3. **Sign-in through an outside service (for example, a Google account)**: no passwords to store, but the client asked for their own accounts with a password, and it adds an external service.

## Maintainability after delivery

- Weight: the same as fit: the requirements do not say who maintains the deliverable.
- Less known choice: no.

| Option | Use | Modern | Documentation | People | Stability |
|---|---|---|---|---|---|
| Server sessions, Argon2id from `golang.org/x/crypto` | `golang.org/x/crypto`: 3,361 stars on its GitHub mirror, latest release 2026-11-11 (github.com/golang/crypto, proxy.golang.org, checked 2026-11-28); the sessions use only Go's standard library | "If you aren't sure which function you need, use Argon2id (IDKey)" (pkg.go.dev/golang.org/x/crypto/argon2, checked 2026-11-28) | that package documentation (checked 2026-11-28) | part of the Go project's own packages, which any Go developer can read up on there | the version is pinned; one function of the package is used |
| Signed tokens (JWT) | not compared: it does not fit (signing out cannot end a token before it expires, AC-1) | | | | |
| Outside service | not compared: it does not fit (the client asked for their own accounts with a password) | | | | |

## Decision

Sessions stored on the server, with an `HttpOnly`, `Secure`, `SameSite=Lax` cookie; passwords hashed with Argon2id (option 1). A session ends after 7 days, or when the person signs out.

## Reasons

- Signing out works immediately, which the client can check by hand (AC-1).
- Injected code in the page cannot read the session cookie, so it cannot take the session elsewhere. It can still send requests from the victim's open page while it runs, which is why titles are never rendered as HTML (threat T-4).
- A copied database gives only Argon2id hashes, which make each password guess slow. Weak passwords can still be guessed, which is why passwords need at least 12 characters (R-1).
- The dependency check passed: `golang.org/x/crypto`, at the version pinned in `api/go.mod`, exists, is maintained by the Go team, and uses the BSD-3-Clause license. Its one OSV entry (GO-0000-0001, checked 2026-11-08) is in the `openpgp` package, which the app does not import; only the `argon2` package is used, and `govulncheck` reports the entry as not called.

## Consequences

- The API keeps a sessions table and checks the session on every request except sign-up and sign-in.
- The 7-day session length came from decision card 1, answered by the client.
