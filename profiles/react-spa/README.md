# `react-spa` profile

What "verified" means for a React single-page application built with Vite, for the MVP gate ("Stack Profiles" in [`docs/design/stack-profiles.md`](../../docs/design/stack-profiles.md), [ADR 0003](../../docs/adr/0003-first-stack-profiles.md)). [`profile.json`](profile.json) is what the gate runs, in the format of [ADR 0028](../../docs/adr/0028-gate-interface.md); this file is what the roles read: the tools it approves, where QA's tests live, how the tests are counted, and what it does not check.

A part with this profile is a folder that holds one npm project in TypeScript: its `package.json` and its `package-lock.json` (lockfile version 2 or 3, from npm 7 or later), named in `keyturn/config.json` as `{"path": "<folder>", "profile": "react-spa"}`. npm workspaces and packages from local folders are not supported.

## What the gate runs

Before the checks, the gate's `pinned-tools` check compares the profile's tools in `package-lock.json` at the head with the newest commit named as `conventions`' (or, without one, the base), and fails when a version changed, or a tool was added or removed ([ADR 0040](../../docs/adr/0040-profile-tools-at-conventions-versions.md); see "Tools"), and its `install-scripts` check reads every package with `"hasInstallScript": true` in `package-lock.json` (direct or indirect, but not the part's own entry) and fails on one that is not at the base at that version, unless an ADR accepted where the gate reads the ADRs has `- Allows install scripts: <package>@<version>` for it ([ADR 0056](../../docs/adr/0056-gate-fails-new-packages-with-install-scripts.md); see "Installing packages"). Both read committed files only. Then, in the part's folder, at the head of the range, the setup, then the checks in this order:

| Step | Command | Fails when |
|---|---|---|
| setup | `rm -rf node_modules`, then `npm ci --ignore-scripts` when there is a `package.json` | the lock file is missing or does not match `package.json`; no package's install scripts run, and nothing committed under `node_modules/` is used |
| `files` | `git ls-files` | a committed file is inside a `node_modules` folder, or a `.gitignore` names it (some checks skip such files) |
| `packages` | reads `package-lock.json`, and `node_modules/.package-lock.json` (what `npm ci` installed) | there is no `package.json`, or there is an `npm-shrinkwrap.json` (which npm would install from instead); or a package does not come from the npm registry at exactly `https://registry.npmjs.org/<name>/-/<name>-<version>.tgz` with an integrity hash: a package from a local folder, a link, a Git repository, another host, or an alias (`"vitest": "npm:other@1"`), any of which could replace a tool the checks run |
| `format` | `prettier --check --no-editorconfig .` | a file is not formatted as Prettier formats it (the files are listed) |
| `typecheck` | `tsc --build --force` | TypeScript reports an error in a project `tsconfig.json` names |
| `lint` | `eslint --config <config> .` | a committed JavaScript or TypeScript file gets no ESLint config, or no rule that is on, unless the config ignores it; there is an `eslint-suppressions.json` (ESLint's bulk suppressions, which would turn errors off without an ADR); or ESLint reports an error |
| `test` | `vitest run --config <config> --allowOnly=false --passWithNoTests=false` | a test fails, a test file does not load, a test is marked `.only`, or there are no tests; QA's tests run here too |
| `build` | `vite build` | the application does not build |

Each tool runs from the part's `node_modules`, by its own package's file (for example `node node_modules/vitest/vitest.mjs`), never through `npm run` or `node_modules/.bin`, so neither a `package.json` script nor another package's command can take its place ([ADR 0028](../../docs/adr/0028-gate-interface.md)). The `format` check runs before `build`, so the build output is never checked for formatting.

The gate reads each config from the part's folder only: the ESLint config (`eslint.config.js`, or `.mjs`, `.cjs`, `.ts`, `.mts`, `.cts`) and the Vitest config (`vitest.config.ts`, or `.mts`, `.cts`, `.js`, `.mjs`, `.cjs`) must be there, and the gate fails the check without them. The Prettier config is passed with `--config` when the part has one (`.prettierrc` in any of its forms, or `prettier.config.*`); without one, Prettier's defaults apply, and a config above the part, in `package.json`, or in `.editorconfig` is never used. The configs load their plugins from the part's `node_modules`, which is why they live in the part's folder.

The gate also records the versions of Node.js, npm, Vite, Vitest, ESLint, TypeScript, and Prettier that ran, in its output and its log ([ADR 0037](../../docs/adr/0037-gate-records-tool-versions.md)). It does not pin them: they are the ones the project's lock file names.

## Tools

Install them before the gate runs; it stops with exit code 2 and says how when one is missing.

- **Toolchain** (covered by approving the stack, ADR 0015): Node.js at the version the design names (the newest LTS release, [ADR 0054](../../docs/adr/0054-newest-stable-versions-checked-against-the-runtime.md)), with npm. The gate does not check that the Node.js on `PATH` is that version (see below).
- **Runtime** (part of the deliverable, so the client agrees to them through the design, ADR 0015): React, `react-dom`, Vite, and `@vitejs/plugin-react`.
- **Profile tools** (approved by this profile, ADR 0015; the design still lists each with its kind and a passing check), installed as development dependencies of the part:
  - type checking: `typescript` (at a version `typescript-eslint` supports: 6.0, since TypeScript 7 is not supported by it yet), `@types/react`, `@types/react-dom`, `@types/node`;
  - linting: `eslint`, `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals`;
  - formatting: `prettier`;
  - tests: `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/dom`, `@testing-library/user-event`, `@testing-library/jest-dom`.

`conventions` installs every profile tool the design lists, at the design's version, in the part's folder (`npm install --save-dev --save-exact --ignore-scripts <tool>@<version> ...`), and commits `package.json` and `package-lock.json` (creating them in a new project). The developer installs the runtime dependencies, and never adds, removes, or changes the version of a profile tool: the `pinned-tools` check fails on any change to the version in the lock file of a profile tool above, or of a package in the `@typescript-eslint/`, `@vitest/`, or `@eslint/` scopes, wherever it is installed (also inside another package's `node_modules`) (which an npm `overrides` entry could change without changing the tool's own version), compared with the newest `conventions` commit. A newer version is a change to the conventions.

Any other development tool is an other tool: it needs the client's agreement through the design. That includes a browser test tool (such as Playwright): the gate does not run one. The project template that `npm create vite` makes uses `oxlint` and TypeScript 7; with this profile, use ESLint and TypeScript 6 instead.

## Installing packages

Every role installs packages without running their install scripts ([ADR 0055](../../docs/adr/0055-installs-skip-install-scripts.md)): pass `--ignore-scripts` to every npm command that installs or changes packages (`npm install`, `npm ci`, `npm update`, `npm uninstall`, `npm dedupe`, `npm audit fix`) (for example `npm install --save-exact --ignore-scripts <package>@<version>`, or `npm ci --ignore-scripts` in a fresh clone), whatever another document says, and never `npx`, `npm exec`, `npm create`, or `npm init <initializer>`, which download a package and run it. It skips each package's `preinstall`, `install`, and `postinstall` scripts, and the part's own lifecycle scripts in `package.json` (such as `prepare`). Vite, Vitest, and the profile's tools work without them, as the gate's setup shows.

A package that runs scripts on install has `"hasInstallScript": true` in its entry in `package-lock.json`, direct or indirect. Its script runs only when an accepted ADR of the project has the line `- Allows install scripts: <package>@<version>` for the version the lock file names, and then alone, in the part's folder: `npm rebuild --ignore-scripts=false <package>@<version>` (`--ignore-scripts=false` makes it run the script even where a person's own npm config sets `ignore-scripts`). Never run `npm rebuild` without a package, which runs every package's script. A package whose script the deliverable needs, without such a line, is reported to the architect; the gate's `install-scripts` check fails a new one that has none.

## Where the rules go

`conventions` writes every rule in these files, in the part's folder:

- **`eslint.config.js`**: the recommended rules of `@eslint/js` and `typescript-eslint`, `eslint-plugin-react-hooks`, the readability limits (`complexity`, `max-lines-per-function`, `max-depth`), boundaries between parts (`no-restricted-imports`), and forbidden patterns (`no-restricted-syntax`, such as `dangerouslySetInnerHTML`). Its `files` must cover every JavaScript and TypeScript file in the part, the config files included (`**/*.{js,jsx,mjs,cjs,ts,tsx,mts,cts}`): the `lint` check fails on a committed file that gets no config or no rule. Ignore only build output (`dist/`) and generated code.
- **The Prettier config** (for example `.prettierrc.json`), if the defaults are not used.
- **`tsconfig.json`** and the files it references (for example `tsconfig.app.json` and `tsconfig.node.json`): `strict` and the other compiler checks. Include the folder of QA's tests (`qa`) as well as `src`, so QA's tests are type-checked too.
- **`vitest.config.ts`**: `include` names the developer's tests (for example `src/**/*.test.{ts,tsx}`) and every QA test (`qa/**/*.test.{ts,tsx}`); `environment: 'jsdom'`. A setup file, if any, is `vitest.setup.ts` next to it. It never imports `vite.config.ts`, which the developer may change: the tests run with the conventions' config only.
- **`.gitignore`**: `node_modules/` and `dist/` ([ADR 0039](../../docs/adr/0039-conventions-writes-gitignore.md)).

`vite.config.ts` is the developer's: it builds the application, and the design names it under "Areas the work may change" when the work needs it (for example, a development server's proxy). It is not read by the tests.

Every file named under `protected` in `profile.json` may change only in the standards role's commits, wherever it is in the repository: the ESLint configs (`eslint.config.*`, `.eslintrc*`, `.eslintignore`), the Prettier configs (`.prettierrc*`, `prettier.config.*`, `.prettierignore`), `tsconfig*.json` and `jsconfig*.json`, the Vitest files (`vitest.config.*`, `vitest.workspace.*`, `vitest.setup.*`), `.npmrc` (which could point npm at another registry), `eslint-suppressions.json`, and Semgrep rule files (`.semgrep.yml`, `.semgrep.yaml`, `.semgrep/`). Every `.gitignore` is protected by the gate itself. The gate does not run Semgrep during the MVP: a rule only Semgrep can express is not enforced yet, and is listed in `conventions.md` as waiting.

## QA's tests

QA's tests live in `qa/` at the root of the part (for a part `web`, `web/qa/**`), as Vitest test files whose names end in `.test.ts` or `.test.tsx`. They test the pages and the code through what the application's modules export (for example, rendering an exported component with Testing Library in `jsdom`), never by changing the application's code. `vitest run` runs them with the rest, so a failing QA test fails the `test` check. The design names this folder under "QA's tests", and never under "Areas the work may change": list the developer's paths in the part one by one (`web/src/**`, `web/index.html`, `web/package.json`, `web/package-lock.json`, `web/vite.config.ts`, `web/public/**`), never `web/**`.

## How the tests are counted

`vitest list --json` with the Vitest config lists every test Vitest would run, and the count is the number of entries. A test marked `.skip` or `.todo` is not counted, so skipping an existing test is a drop in the count. A test written with `.each` counts once, however many rows it has. A part's folder that is not there yet, or that has no `package.json` yet (for example, only the conventions' configs), counts 0. A count that cannot run (for example, a test file that does not load) fails the `test-count` check.

## Suppressions

An added line in a JavaScript, TypeScript, CSS, or HTML file fails the `suppressions` check when it has `eslint-disable` (in any form), an inline ESLint config comment (`/* eslint <rule>: off */`, `/* eslint-env */`, `/* global */`, also when `eslint` or `global` starts a later line of the comment), `@ts-ignore`, `@ts-nocheck`, or `@ts-expect-error`, `prettier-ignore`, or `fails` (Vitest's `it.fails` and `test.fails`, which pass when the test fails, also written `it['fails']` or taken with `const { fails } = it`), unless an accepted ADR allows it (ADR 0028). The line names the ADR (`// eslint-disable-next-line no-console -- ADR-0005`), or the ADR allows it in a folder (`- Allows in web/src/api/generated/**: /* eslint-disable */`, [ADR 0038](../../docs/adr/0038-suppressions-allowed-in-a-folder.md)), which is how generated code that carries such a comment is allowed.

## What this profile does not check

Each delivery report made with this profile lists these under "What was not verified":

- **Security checks**: no SAST (for example Semgrep rules or ESLint security plugins), no scan of the packages for known vulnerabilities (`npm audit` or OSV), and no secret scanning, until phase 5.
- **Packages**: the `packages` check makes sure every package comes from the npm registry under its own name, and `pinned-tools` keeps the profile's tools where `conventions` put them; neither checks that a runtime dependency is a version the design lists, or that the design lists it at all, and the other indirect dependencies may change; the review reads changes to `package.json`.
- **Hand-written code in a generated folder**: an ADR that allows a suppression in a generated code's folder ([ADR 0038](../../docs/adr/0038-suppressions-allowed-in-a-folder.md)) allows it on every line there, so code the developer writes by hand in that folder, with the same comment, passes the gate; and the gate does not run the generator to compare its output. The review reads what changed in such a folder.
- **Tests**: coverage is not checked; a Vitest modifier such as `fails` reached in a way the suppression patterns do not read (for example, through a variable holding its name) is not found; a test written with `.each` counts once, so a dropped row is not found; a test replaced with a weaker one under the same name is not found.
- **Code that runs during the tests and the build**: the tests run the application's code, which can change what the test tools do (for example, by changing `expect`); `vite build` runs `vite.config.ts` and its plugins; the packages' own code runs in every check. The gate does not stop code that changes how the checks run; the review and the security review read it.
- **Type checking**: `tsc` checks the files `tsconfig.json` reaches. JavaScript files are linted but not type-checked, unless the conventions turn on `checkJs`.
- **Browsers**: no test runs in a real browser; `jsdom` stands in for one. A page that works in `jsdom` and fails in a browser is not found.
- **Install scripts**: the gate never runs them, and `install-scripts` trusts the mark in `package-lock.json`: a lock file edited to drop a package's `hasInstallScript` is not found (`packages` checks where each package comes from and its integrity hash, not its mark). The part's own `preinstall`, `install`, `postinstall`, and `prepare` scripts in `package.json` are not checked; nothing of keyturn runs them, and the review reads changes to `package.json`.
- **The Node.js version**: the gate uses the Node.js on `PATH`, whatever the design's "Stack" or `engines` in `package.json` asks for (fixing it waits for #133).
- **Structure and secure defaults**: this profile does not give a recommended project structure or secure defaults yet; the architect takes them from React's and Vite's own documentation and says so in the stack's ADR.
