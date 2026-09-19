# DEC-105 — M44 User Notification Preferences & Delivery Controls Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M44

## Context

The project now has:

- durable alert candidates and alert delivery boundaries;
- Telegram as the first concrete notification provider;
- automatic alert delivery after completed analysis;
- scheduled automatic delivery;
- multi-user identity, ownership, authentication, credential lifecycle, and user-facing audit history.

User-specific notification preferences were intentionally deferred by the earlier notification milestones because the system did not yet have a stable multi-user ownership boundary.

M38–M43 now establish that boundary. The next candidate capability is therefore to define how an authenticated user controls which existing alert-delivery behavior applies to that user without moving notification policy into the analytical domain.

This document is a design proposal only. It does not authorize implementation.

## Problem

Current notification delivery semantics are application-wide and were designed before multi-user ownership existed.

The system now needs an explicit answer to questions such as:

- Which user receives an alert?
- Which notification channels are enabled for a user?
- Can a user disable automatic delivery without disabling alert generation?
- What happens when a user has no configured delivery channel?
- How are credentials/provider settings separated from user preferences?
- How do preferences interact with scheduled automatic delivery?
- What audit evidence is required for preference changes?
- Should preferences be global per user or scoped to a market/alert type?

These questions should be resolved before adding user-specific notification behavior.

## Desired Outcome

Define a user-owned notification-preference capability that:

1. controls delivery policy without changing analytical alert generation;
2. remains independent of concrete providers such as Telegram;
3. is durable and survives application restart;
4. is explicitly scoped to an authenticated user;
5. composes with existing automatic and scheduled delivery capabilities;
6. preserves existing delivery idempotency semantics;
7. provides deterministic behavior when preferences are missing or incomplete;
8. exposes management through application/API/dashboard boundaries rather than embedding policy in React or FastAPI.

## Scope

### In scope

- user ownership of notification preferences;
- enabled/disabled delivery policy;
- channel preference semantics;
- default behavior for new users;
- interaction with automatic alert delivery;
- interaction with scheduled automatic delivery;
- persistence boundary;
- authorization boundary;
- audit requirements for preference changes;
- deterministic read/update behavior;
- testability.

### Explicitly out of scope

- new notification providers;
- provider-specific credential management;
- notification content redesign;
- changing alert-generation rules;
- changing opportunity classification;
- AI-based notification decisions;
- bulk marketing notifications;
- arbitrary user-defined rules/strategies;
- delivery analytics;
- queue/distributed delivery;
- trading execution;
- mobile push infrastructure.

## Existing Boundary

The target direction is:

```
AlertCandidate
      ↓
Automatic / Scheduled Delivery Policy
      ↓
User Notification Preferences
      ↓
DeliverAlert
      ↓
Provider
```

Preferences must influence delivery eligibility, not alert generation.

## Alternatives

### A — Global notification settings only

One global configuration controls delivery for the whole installation.

**Trade-offs:**
- simplest implementation;
- unsuitable for a multi-user product;
- cannot express independent user preferences;
- creates cross-user coupling.

**Assessment:** Not sufficient for the current multi-user architecture.

### B — User-owned preference aggregate

Each active user owns one durable notification-preference record.

**Trade-offs:**
- clear ownership;
- simple authorization model;
- reusable across API/dashboard/scheduled delivery;
- requires a persistence boundary and explicit defaults.

**Assessment:** Preferred candidate.

### C — Preferences embedded inside User

Store notification settings directly on the User entity.

**Trade-offs:**
- fewer application components;
- couples identity lifecycle to notification policy;
- makes notification concerns part of the identity model;
- harder to evolve when channels/preferences grow.

**Assessment:** Not preferred.

### D — Provider-specific settings as preferences

Let each provider own its own user settings.

**Trade-offs:**
- convenient for provider-specific behavior;
- leaks infrastructure concerns into user policy;
- makes multi-provider behavior inconsistent;
- complicates authorization and portability.

**Assessment:** Not selected.

## Open Questions

These must be resolved before implementation:

1. **Default policy:** Are notifications enabled by default for newly created users, or explicitly opt-in?
2. **Channel model:** Should the MVP support only the existing Telegram channel, or define a provider-neutral channel enum with Telegram as the first implementation?
3. **Delivery scope:** Should preferences apply to all alert candidates or distinguish alert types such as BUY only?
4. **Scheduled delivery:** Should scheduled automatic delivery skip users whose preferences disable the relevant channel?
5. **Missing preference:** What deterministic behavior applies if a user has no preference record?
6. **Credential boundary:** Should Telegram destination/credential configuration remain deployment-level, or become user-owned in a separate future gate?
7. **Audit:** Should every preference mutation create a management-audit event, and which action names should be introduced?
8. **Deletion/disablement:** What happens to preferences when a user becomes DISABLED or DELETED?
9. **API shape:** Separate GET/PUT resource under `/api/v1/users/me/notifications`, or a broader user-settings resource?
10. **Concurrency/idempotency:** Should updates use full replacement semantics, patch semantics, or optimistic versioning?

## Proposed Invariants

Unless a later decision changes them:

1. Alert generation remains independent of user notification preferences.
2. Preferences are user-owned application state.
3. Provider-specific credentials remain outside the preference model.
4. A disabled preference prevents delivery but does not delete or suppress the underlying alert candidate.
5. Missing preference behavior is explicit and deterministic.
6. Ownership authorization is centralized in the application layer.
7. Dashboard code does not implement notification policy.
8. Preference updates are durable and auditable.
9. Existing delivery idempotency remains authoritative.
10. No new provider is introduced by M44.

## TDD Acceptance Shape

Before implementation, tests should establish at least:

- default preference behavior for a newly created user;
- authenticated user can read only their own preferences;
- authenticated user can update only their own preferences;
- unauthenticated access is rejected;
- unrelated user access is rejected;
- disabled channel prevents eligible delivery;
- enabled channel permits eligible delivery;
- missing preferences follow the accepted default;
- scheduled automatic delivery respects the accepted preference policy;
- alert generation remains unchanged when delivery is disabled;
- preference changes survive restart;
- preference mutations produce the accepted audit evidence;
- provider-specific credential data is not exposed by the preference API.

## Revisit Conditions

Revisit this gate if:

- multiple notification providers require materially different policy semantics;
- notification preferences become strategy/rule configuration;
- organizations or delegated notification management are introduced;
- delivery becomes asynchronous/distributed;
- provider credentials become user-owned;
- mobile push requires a separate device-registration model.

## Design Gate Decision

**Status: Proposed — implementation is not authorized.**

M44 implementation must not begin until the open questions above are resolved and the accepted boundary is recorded in this document and the project decision log.
