# 0004. React and Vite for the web client

- Status: accepted
- Date: 2026-11-08
- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-8, R-9, R-10
- Needs client agreement: yes

## Context

The web client needs sign-up, sign-in, and task pages that call the Go API. The available frontend profile is `react-spa` (ADR 0003 in keyturn), which uses React and builds with Vite. Both are new dependencies for this project, and every new dependency needs the client's approval and a recorded check.

## Options considered

1. **React with Vite (`react-spa`)**: the gate has a profile for it, React renders text safely by default (titles are never treated as HTML unless code asks for it), and the built result is static files served by the Go program. Three new dependencies: `react`, `react-dom`, and `vite` (used only to build).
2. **Plain HTML and JavaScript, no framework**: no dependencies, but every page update is written by hand, which is where text is most often inserted as HTML by mistake (threat T-4), and there is no stack profile for it, so the gate's coverage would be limited.

## Maintainability after delivery

- Weight: the same as fit: the requirements do not say who maintains the deliverable.
- Less known choice: no.

| Option | Use | Modern | Documentation | People | Stability |
|---|---|---|---|---|---|
| React with Vite | `react`: 252,836 stars, 255 million npm downloads in the week to 2026-11-27, latest release 2026-10-14; `vite`: 84,169 stars, 270 million downloads that week, latest release 2026-11-26 (github.com, api.npmjs.org, registry.npmjs.org, checked 2026-11-28) | React's documentation recommends a framework for a new app, and still documents building one from scratch with a build tool such as Vite, which fits three pages served by the Go program (react.dev, "Creating a React App" and "Build a React app from Scratch", checked 2026-11-28) | both projects' own guides (react.dev, vite.dev, checked 2026-11-28) | very many people know both (their stars and downloads) | the versions are pinned; an update is a dependency change, checked again |
| Plain HTML and JavaScript | the browser's own features, but every page update is code of the project's own: no use, documentation, or people outside it | | only what the project writes | whoever maintains it must first work out how the project's own page updates work | the project's code, maintained by hand |

## Decision

React with Vite, following the `react-spa` profile, at the versions pinned in `web/package.json` (option 1).

## Reasons

- The gate fully covers the profile, so the web client is checked like the API.
- Rendering titles as text is the default, which is the main mitigation for T-4.
- The dependency check passed for all three: they exist, are actively maintained, have no OSV entries for the versions chosen (checked 2026-11-08), and use the MIT license. The versions are pinned, so a later update is a dependency change that is checked again.

## Consequences

- The client approves these dependencies in the design summary (decision 0004) before work on the web client starts.
- Updating React or Vite later is a dependency change, checked again by the gate.
