# Design answers

Points the design left open, found after the work started, and the architect's answers. They fill in what the design leaves open, and change nothing it decides. Read them with the [design](design.md).

## A-1

- What the design left open: the module path that `api/go.mod` declares. The design names the API's folders and its two dependencies, but not the module's own path.
- Answer: `example.com/taskmanager/api`. The module is never imported from outside this repository, so the path only has to be unique within it; the packages are then `example.com/taskmanager/api/internal/account` and so on.
- Why it changes nothing: "Stack" and "Structure" in the design fix the folders and the dependencies, not the module's name, and no requirement, interface, or threat depends on it.
- Answered by: the architect
- Reads with the design at: `b7e44103f31bad9654d8e75f3a7bc30708f7732d`
- Round: 1
- Date: 2026-11-08
