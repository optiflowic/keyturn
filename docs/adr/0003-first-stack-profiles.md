# 0003. First stack profiles: `go` and `react-spa`

- Status: accepted
- Date: 2026-11-07

## Context

Stack profiles define what "verified" means for one tech stack (see "Stack Profiles" in `docs/DESIGN.md`). Phase 4 starts with one backend and one frontend profile, enough to validate new-project mode end to end on a web application. Profiles are added one at a time, so the first two shape the gate and every later profile.

The candidates are the planned profiles: Go, Python, and Rust for the backend; React (SPA), Next.js, and React Router v7+ for the frontend.

## Options considered

Backend:

1. **Go**: static types, a single fast toolchain (`go build`, `go test`, `go vet`), and mature security tooling (`govulncheck`, `gosec`). Small standard library surface for web servers.
2. **Python**: very common, but type checking and packaging are split across several tools, which makes "verified" harder to define in the first profile.
3. **Rust**: strong safety guarantees and good tooling, but longer build times slow down the test-and-fix loop that the gate runs many times per task.

Frontend:

1. **React SPA with Vite (`react-spa`)**: a static client with a clear boundary to the backend API. The smallest set of moving parts (no server rendering, no framework routing conventions).
2. **Next.js**: popular, but mixes server and client code, which adds a second backend surface to secure and test in the very first profile.
3. **React Router v7+ (framework mode)**: similar trade-off to Next.js.

## Decision

The first two profiles are `go` (backend) and `react-spa` (React with Vite, frontend).

## Reasons

- Both stacks have mature, scriptable checks for tests, linting, and security scanning, which is what the gate needs first.
- A Go API plus a static React client keeps a clean, single trust boundary between frontend and backend. That makes the first threat models and security checks simpler and easier to verify.
- Starting with the simplest frontend avoids building server-rendering concerns into the gate before the basic loop works. Next.js and React Router can be added later as their own profiles.

## Consequences

- Phase 4 builds `profiles/go/` and `profiles/react-spa/`, and phase 6 validates new-project mode on these two stacks.
- Gate design is validated against two quite different toolchains (Go modules and npm), which helps keep it stack-neutral.
- Projects that need server rendering, Python, or Rust wait for later profiles, or run with limited gate coverage stated in the delivery report.
