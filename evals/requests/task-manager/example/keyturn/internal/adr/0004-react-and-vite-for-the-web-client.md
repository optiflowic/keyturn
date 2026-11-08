# 0004. React and Vite for the web client

- Status: accepted
- Date: 2026-11-08
- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-8, R-9
- Needs client agreement: yes

## Context

The web client needs sign-up, sign-in, and task pages that call the Go API. The available frontend profile is `react-spa` (ADR 0003 in keyturn), which uses React and builds with Vite. Both are new dependencies for this project, and every new dependency needs the client's approval and a recorded check.

## Options considered

1. **React with Vite (`react-spa`)**: the gate has a profile for it, React renders text safely by default (titles are never treated as HTML unless code asks for it), and the built result is static files served by the Go program. Three new dependencies: `react`, `react-dom`, and `vite` (used only to build).
2. **Plain HTML and JavaScript, no framework**: no dependencies, but every page update is written by hand, which is where text is most often inserted as HTML by mistake (threat T-4), and there is no stack profile for it, so the gate's coverage would be limited.

## Decision

React 18 with Vite 5, following the `react-spa` profile (option 1).

## Reasons

- The gate fully covers the profile, so the web client is checked like the API.
- Rendering titles as text is the default, which is the main mitigation for T-4.
- The dependency check passed for all three: they exist, are actively maintained, have no OSV entries for the versions used, and use the MIT license.

## Consequences

- The client approves these dependencies in the design summary (decision 0004) before work on the web client starts.
- Updating React or Vite later is a dependency change, checked again by the gate.
