# Timestamp conventions

- Persisted instants (credential, workflow, acquisition, audit, and conflict event timestamps) should be timezone-aware UTC values.
- EGX trading-session dates are calendar dates in the `Africa/Cairo` timezone and must not be inferred from the server's local timezone.
- Provider bar timestamps must retain their source semantics and be normalized only by an explicit, tested adapter rule.
- Do not use `datetime.now()`, `datetime.utcnow()`, or `date.today()` for production event/session logic without an explicit timezone policy.

This change fixes the known conflict-event timestamp that previously depended on the host's local timezone. The CI datetime lint gate is being added separately to identify remaining naive-date/time usage before broader replacements.
