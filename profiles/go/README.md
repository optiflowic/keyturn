# `go` profile

What "verified" means for a Go part, for the MVP gate ("Stack Profiles" in [`docs/design/stack-profiles.md`](../../docs/design/stack-profiles.md), [ADR 0003](../../docs/adr/0003-first-stack-profiles.md)). [`profile.json`](profile.json) is what the gate runs, in the format of [ADR 0028](../../docs/adr/0028-gate-interface.md); this file is what the roles read: the tools it approves, where QA's tests live, how the tests are counted, and what it does not check.

A part with this profile is a folder that holds one Go module (its `go.mod`), named in `keyturn/config.json` as `{"path": "<folder>", "profile": "go"}`.

## What the gate runs

In the part's folder, at the head of the range, in this order:

| Check | Command | Fails when |
|---|---|---|
| `module` | `go mod edit -json` | `go.mod` has an `ignore` directive, which would hide folders (QA's included) from every `./...` below, or a `replace` to a folder, whose code the gate does not check (replace with a module version instead) |
| `build` | `go build ./...` | a package does not compile |
| `test` | `go test -count=1 ./...` | a test fails, or a test package does not compile; QA's tests run here too |
| `format` | `gofmt -l .` | a Go file is not formatted as `gofmt` formats it (the files are listed) |
| `vet` | `go vet ./...` | `go vet` reports a problem |
| `lint` | `golangci-lint run --config <file> ./...` | a linter the project's config turns on reports a problem |

Every `go` and `golangci-lint` command runs with `GOWORK=off` and `GOFLAGS=-mod=readonly`. A `go.work` file anywhere above the part is not used, so it cannot swap a module for other code. A committed `vendor/` folder is not used either, and every module is checked against `go.sum`.

No `setup` step: `go build` and `go test` download the modules that `go.mod` and `go.sum` name.

The gate looks for the `golangci-lint` config in the part's folder, then in each folder above it up to the repository root, and passes the first one it finds with `--config`. Without one, it passes `--no-config`, and `golangci-lint` runs its default linters: a config outside the repository (in a folder above it, or in the home folder) is never used. The config is the standards role's (`conventions`): every limit and rule `conventions` sets for Go goes there.

## Tools

Install them before the gate runs; it stops with exit code 2 and says how when one is missing.

- **Toolchain** (covered by approving the stack, ADR 0015): Go 1.24 or later, with `gofmt` and `go vet`, and the standard library's `testing` and `net/http/httptest` for tests.
- **Profile tools** (approved by this profile, ADR 0015; the design still lists each with its kind and a passing check): `golangci-lint` v2 (2.0 or later), with the linters it ships (for example `staticcheck`, `errcheck`, `unused`, `gocyclo`, `funlen`, `nestif`, `depguard`, and `forbidigo`).

Any other development tool, a test library such as `testify` included, is an other tool: it needs the client's agreement through the design.

## Where the rules go

`conventions` writes the Go rules in the `golangci-lint` config (`.golangci.yml`, in v2's format):

- readability limits with `gocyclo` (complexity), `funlen` (function length), and `nestif` (nesting);
- boundaries between parts with `depguard` (which package may import which);
- forbidden patterns with `forbidigo` (calls the design or the threat model forbids).

Every file named under `protected` in `profile.json` may change only in the standards role's commits: the `golangci-lint` configs (`.golangci.yml`, `.yaml`, `.toml`, `.json`), `staticcheck.conf`, and Semgrep rule files (`.semgrep.yml`, `.semgrep.yaml`, `.semgrep/`), wherever they are in the repository. A config `conventions` writes under any other name stops the gate (the commit changes a path a `conventions` commit may not), so write the rules only in these files. The gate does not run Semgrep during the MVP: a rule only Semgrep can express is not enforced yet, and is listed in `conventions.md` as waiting.

## QA's tests

QA's tests live in `qa/` at the root of the part (for a part `api`, `api/qa/**`), as a Go package of their own whose files all end in `_test.go`. They test the deliverable through what it exports or through its HTTP interface (for example, with `net/http/httptest` on the exported handler), never through its unexported code. `go test ./...` runs them with the rest, so a failing QA test fails the `test` check. The design names this folder under "QA's tests", and never under "Areas the work may change".

## How the tests are counted

`go test -list . ./...` lists the top-level `Test`, `Fuzz`, and `Example` functions of every package in the part (benchmarks are not counted), and the count is the number of those names. A part's folder that is not there yet counts 0. A count that cannot run (for example, a test package that does not compile) fails the `test-count` check.

## Suppressions

An added line in a `.go` file fails the `suppressions` check when it has `//nolint`, `//lint:ignore` or `//lint:file-ignore` (staticcheck), `#nosec` (gosec), or a generated-file mark (`Code generated ... DO NOT EDIT`, which makes `golangci-lint` skip the whole file), unless it names an accepted ADR that allows it (ADR 0028). Generated code therefore needs an accepted ADR that allows its mark.

## What this profile does not check

Each delivery report made with this profile lists these under "What was not verified":

- **Security checks**: no SAST (for example `gosec` or Semgrep rules), no scan of the modules for known vulnerabilities (`govulncheck`), and no secret scanning, until phase 5.
- **Tests**: subtests (`t.Run`) are not counted, so a dropped subtest is not found; skipped tests (`t.Skip`) and coverage are not checked.
- **Code that runs during the tests**: `go test` runs the project's own code, including `init` functions and `TestMain` in the developer's packages. The gate does not stop code that changes how the tests run; the review and the security review read it.
- **Builds outside the default**: files behind a build constraint (`//go:build`) that the default build leaves out are not built, tested, or linted.
- **Code that `./...` does not reach**: a folder inside the part with its own `go.mod` (a nested module), and folders whose names start with `.` or `_` or are named `testdata`, are not built, tested, linted, or counted. The review reads any new `go.mod` in the change.
- **The toolchain the module asks for**: a `toolchain` line in `go.mod` can make `go` download and run another Go version, with the network the gate runs in.
- **Structure and secure defaults**: this profile does not give a recommended project structure or secure defaults yet; the architect takes them from Go's own documentation and says so in the stack's ADR.
