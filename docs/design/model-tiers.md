# Model Tiers

Not every step needs the most capable model.

- **Lower-tier models do the bulk of the work** where the task is well defined: implementation of a clear design, test writing, translation, routine fixes.
- **Higher-tier models evaluate** what needs judgment: requirements, design, and the review of the lower-tier model's output (design fit, readability, things the tools cannot check).
- **Escalate on failure.** If a lower-tier model fails the same step repeatedly, the step is retried with a higher-tier model before the rework limit is reached.
- This does not replace the mechanical gates. The higher-tier review covers what the tools cannot check; pass/fail still comes from the gates.
- The model for each role is configurable per project. Usage is recorded per role so the tiering can be tuned with real data.
