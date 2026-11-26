# keyturn Design Principles

This document describes how keyturn is designed. All implementation work should follow it.

The design is split into one file per section, in [`docs/design/`](design/). This page is its index: read it, then only the sections your work relates to, and always [Phases](design/phases.md). Every heading of the earlier single-file design is kept here, each with a link to where its content now lives, so that links to these headings still lead to the right content ([ADR 0021](adr/0021-design-split-into-section-files.md)).

## Concept

[`design/concept.md`](design/concept.md): what keyturn is: AI agents as a contractor team, with the human as the client.

## Design Principles

[`design/principles.md`](design/principles.md): the twelve principles every other section follows.

## Language

[`design/language.md`](design/language.md): which language each document is written in, and local translations with `localize`.

### This repository

In [`design/language.md`](design/language.md#this-repository).

### Projects that use keyturn

In [`design/language.md`](design/language.md#projects-that-use-keyturn).

### Local translations (`localize`)

In [`design/language.md`](design/language.md#local-translations-localize).

#### Reading: English → client's language

In [`design/language.md`](design/language.md#reading-english--clients-language).

#### Writing: client's language → English

In [`design/language.md`](design/language.md#writing-clients-language--english).

#### Approving translated content

In [`design/language.md`](design/language.md#approving-translated-content).

#### Keeping the cost down

In [`design/language.md`](design/language.md#keeping-the-cost-down).

#### Standalone use

In [`design/language.md`](design/language.md#standalone-use).

## Stack Profiles

[`design/stack-profiles.md`](design/stack-profiles.md): what a stack profile defines, and the planned profiles.

### Planned profiles

In [`design/stack-profiles.md`](design/stack-profiles.md#planned-profiles).

## Modes

[`design/modes.md`](design/modes.md): new-project mode and existing-repository mode.

## Repository Structure

[`design/repository-structure.md`](design/repository-structure.md): single- and multi-repository projects, and who creates the repositories.

### Flow

In [`design/repository-structure.md`](design/repository-structure.md#flow).

### Multi-repository projects

In [`design/repository-structure.md`](design/repository-structure.md#multi-repository-projects).

## Delivery Scope

[`design/delivery-scope.md`](design/delivery-scope.md): delivery ends at a merged pull request; deployment stays with the human.

## Changing Requirements

[`design/changing-requirements.md`](design/changing-requirements.md): stable IDs, change requests, and keeping the history of the requirements.

## Documents

[`design/documents.md`](design/documents.md): client-facing and internal documents, the client attention budget, where documents live, and ADRs.

### Client-facing documents

In [`design/documents.md`](design/documents.md#client-facing-documents).

### Client attention budget

In [`design/documents.md`](design/documents.md#client-attention-budget).

### Internal documents

In [`design/documents.md`](design/documents.md#internal-documents).

### Where documents live in a project

In [`design/documents.md`](design/documents.md#where-documents-live-in-a-project).

### Architecture decision records

In [`design/documents.md`](design/documents.md#architecture-decision-records).

## Roles

[`design/roles.md`](design/roles.md): the roles, who checks what, and how each role is used on its own.

### Phase 1 roles

In [`design/roles.md`](design/roles.md#phase-1-roles).

### Architect

In [`design/roles.md`](design/roles.md#architect).

### Who checks what

In [`design/roles.md`](design/roles.md#who-checks-what).

### Security

In [`design/roles.md`](design/roles.md#security).

### Standards

In [`design/roles.md`](design/roles.md#standards).

### Requirements must cover misuse

In [`design/roles.md`](design/roles.md#requirements-must-cover-misuse).

### Requirements must cover the look

In [`design/roles.md`](design/roles.md#requirements-must-cover-the-look).

### Later roles

In [`design/roles.md`](design/roles.md#later-roles).

### Roles are usable on their own

In [`design/roles.md`](design/roles.md#roles-are-usable-on-their-own).

## GitHub Integration

[`design/github-integration.md`](design/github-integration.md): how tasks map to issues, pull requests, and the Project board, and the security rules for unattended agents.

### Mapping

In [`design/github-integration.md`](design/github-integration.md#mapping).

### Flow

In [`design/github-integration.md`](design/github-integration.md#flow).

### Security requirements

In [`design/github-integration.md`](design/github-integration.md#security-requirements).

## Guardrails

[`design/guardrails.md`](design/guardrails.md): the layers that keep agents in check: protected checks, approved scope, dependency checks, the sandbox, budgets and usage limits, and traceability.

### 1. Agents cannot weaken their own checks

In [`design/guardrails.md`](design/guardrails.md#1-agents-cannot-weaken-their-own-checks).

### 2. Scope is limited to what was approved

In [`design/guardrails.md`](design/guardrails.md#2-scope-is-limited-to-what-was-approved).

### 3. New dependencies are checked

In [`design/guardrails.md`](design/guardrails.md#3-new-dependencies-are-checked).

### 4. The environment limits the damage

In [`design/guardrails.md`](design/guardrails.md#4-the-environment-limits-the-damage).

### 5. Budgets and escalation

In [`design/guardrails.md`](design/guardrails.md#5-budgets-and-escalation).

#### Subscription usage limits

In [`design/guardrails.md`](design/guardrails.md#subscription-usage-limits).

### 6. Everything is traceable

In [`design/guardrails.md`](design/guardrails.md#6-everything-is-traceable).

## Resuming Work

[`design/resuming-work.md`](design/resuming-work.md): the task state file, checkpoints, and resuming a stopped task.

## Model Tiers

[`design/model-tiers.md`](design/model-tiers.md): which work goes to lower-tier and higher-tier models.

## External Services

[`design/external-services.md`](design/external-services.md): what keyturn sends outside the AI tool the client already uses.

## Architecture

[`design/architecture.md`](design/architecture.md): skills and subagents, agent instruction files, and gates.

### Separate the "what" from the "who"

In [`design/architecture.md`](design/architecture.md#separate-the-what-from-the-who).

### Agent instruction files

In [`design/architecture.md`](design/architecture.md#agent-instruction-files).

### Gates

In [`design/architecture.md`](design/architecture.md#gates).

## Repository Layout (initial)

[`design/repository-layout.md`](design/repository-layout.md): the folders and files of this repository.

## Evaluation

[`design/evaluation.md`](design/evaluation.md): regression testing of keyturn with evaluation requests and a baseline.

## Client Portal (planned)

[`design/client-portal.md`](design/client-portal.md): the planned GUI for the client.

## Phases

[`design/phases.md`](design/phases.md): the order in which keyturn is built, the MVP that comes first, and when each phase is done.

### MVP

In [`design/phases.md`](design/phases.md#mvp).

### Numbered phases

In [`design/phases.md`](design/phases.md#numbered-phases).

## Future Vision (not in scope yet)

[`design/future-vision.md`](design/future-vision.md): later enhancements, and what to do now to keep them possible.

## Implementation Rules

[`design/implementation-rules.md`](design/implementation-rules.md): rules for keyturn's own code and skills.

## Maintainer Notes

[`design/maintainer-notes.md`](design/maintainer-notes.md): where a maintainer's own plans live.

## Decisions

[`design/decisions.md`](design/decisions.md): where decisions about keyturn are recorded.
