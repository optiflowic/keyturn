# Delivery Scope

- **Delivery ends at a merged pull request.** Deployment and release are done by the human.
- keyturn **does** build the CI/CD setup when the requirements ask for it: build and test workflows, deployment workflows, and a deployment runbook (a client-facing document explaining how to deploy and how to roll back).
- keyturn never holds production credentials and never triggers a deployment. Deployment workflows are designed so that a human starts them (e.g., manual approval or a release tag).
