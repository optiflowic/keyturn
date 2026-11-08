# 0003. Password sign-in with sessions stored on the server

- Status: accepted
- Date: 2026-11-08
- Serves: R-1, R-2, R-7, R-8
- Needs client agreement: yes

## Context

People sign up and sign in with an email address and a password (R-1, R-2), and every request must be tied to one person so that tasks stay private (R-7). This is a change to authentication, which always needs the client's approval. Passwords must be stored so that a stolen database makes them as slow to guess as possible.

## Options considered

1. **Sessions stored on the server, in a cookie that scripts cannot read; passwords hashed with Argon2id from `golang.org/x/crypto`**: signing out ends the session at once, and the cookie cannot be read by code in the page. Argon2id is the current recommendation for password storage. One new dependency, maintained by the Go team.
2. **Signed tokens kept in the browser (JWT)**: no session table, but signing out cannot end a token before it expires, and tokens kept where scripts can read them can be stolen by injected code.
3. **Sign-in through an outside service (for example, a Google account)**: no passwords to store, but the client asked for email and password, and it adds an external service.

## Decision

Sessions stored on the server, with an `HttpOnly`, `Secure`, `SameSite=Lax` cookie; passwords hashed with Argon2id (option 1). A session ends after 7 days, or when the person signs out.

## Reasons

- Signing out works immediately, which the client can check by hand (AC-1).
- Injected code in the page cannot read the session cookie, so it cannot take the session elsewhere. It can still send requests from the victim's open page while it runs, which is why titles are never rendered as HTML (threat T-4).
- A copied database gives only Argon2id hashes, which make each password guess slow. Weak passwords can still be guessed, which is why passwords need at least 12 characters (R-1).
- The dependency check passed: `golang.org/x/crypto` v0.58.0 exists, is maintained by the Go team, and uses the BSD-3-Clause license. Its one OSV entry (GO-2026-5932, checked 2026-11-08) is in the `openpgp` package, which the app does not import; only the `argon2` package is used, and `govulncheck` reports the entry as not called.

## Consequences

- The API keeps a sessions table and checks the session on every request except sign-up and sign-in.
- The 7-day session length came from decision card 1, answered by the client.
