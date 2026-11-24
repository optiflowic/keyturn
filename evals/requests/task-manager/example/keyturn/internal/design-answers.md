# Design answers

Points the design left open, found after the work started, and the architect's answers, threat ratings the architect raised or explained, and answers withdrawn by the maintainer's decision. A withdrawn answer is void. They fill in what the design leaves open, and change nothing it decides except a threat's rating, which only goes up. Read them with the [design](design.md) and the [threat model](threat-model.md).

## A-1

- What the design left open: the module path that `api/go.mod` declares. The design names the API's folders and its two dependencies, but not the module's own path.
- Asked by: implement
- Answer: `example.com/taskmanager/api`. The module is never imported from outside this repository, so the path only has to be unique within it; the packages are then `example.com/taskmanager/api/internal/account` and so on.
- Why it changes nothing: "Stack" and "Structure" in the design fix the folders and the dependencies, not the module's name, and no requirement, interface, or threat depends on it; it changes only `api/go.mod`, inside the API's area, and no rule of the conventions names the module path.
- Answered by: the architect
- Reads with the design at: `b7e44103f31bad9654d8e75f3a7bc30708f7732d`
- Round: 1
- Date: 2026-11-08

## A-2

- What the design left open: where the API's code takes the current time from. The design says that a sign-in block ends 15 minutes after the fifth wrong password (R-8), but not how the code reads the time, which a test needs to reach the end of a block without waiting.
- Asked by: implement
- Answer: `api/internal/http` exports `NewServer(cfg Config)`, with `Config{DBPath string; Now func() time.Time}`; `NewServer` opens the database itself, and `Now` is the only clock the sign-in limit reads. `api/cmd/server` leaves `Now` unset (`time.Now`); a test sets it and moves it forward.
- Why it changes nothing: the design leaves the clock's source open, and no requirement, interface, or threat depends on it; it changes only `api/internal/http/` and `api/cmd/server/`, inside the API's areas.
- Answered by: the architect
- Reads with the design at: `b7e44103f31bad9654d8e75f3a7bc30708f7732d`
- Round: 1
- Date: 2026-11-08

## A-3

- Withdraws: A-2
- Why: A-2 cannot be built: opening the database in `api/internal/http` needs `api/internal/store`, which the conventions' import rule for that package forbids. The maintainer decided to withdraw it and to have the clock answered again.
- In its place: A-4, the entry after this one
- Withdrawn by: the maintainer's decision
- Reads with the design at: `b7e44103f31bad9654d8e75f3a7bc30708f7732d`
- Round: 1
- Date: 2026-11-08

## A-4

- What the design left open: the same gap as A-2, which A-3 withdrew: where the API's code takes the current time from, so that a test can move it to the end of a 15-minute sign-in block (R-8).
- Asked by: implement
- Answer: `api/internal/account` exports `NewService(db *store.Store, now func() time.Time)`, and the sign-in limit reads the time only from `now`. `api/internal/http` exports `NewHandler(accounts *account.Service, tasks *task.Service) http.Handler`, and imports neither `api/internal/store` nor `database/sql`. `api/cmd/server` opens the store and passes `time.Now`; a test opens a store of its own, builds the account service with a clock it moves forward, and serves the handler with `httptest`.
- Why it changes nothing: the design leaves the clock's source open, and puts the sign-in limit in the account service; it changes only `api/internal/account/`, `api/internal/http/`, and `api/cmd/server/`, inside the API's areas, and `api/internal/http` still imports neither `api/internal/store` nor `database/sql`, as the conventions' import rule requires.
- Answered by: the architect
- Reads with the design at: `b7e44103f31bad9654d8e75f3a7bc30708f7732d`
- Round: 1
- Date: 2026-11-08
