# Recovery measurements

Public method overview. The unchanged original contains historical empirical
examples retained privately; those results are not included here.

Retain successful tackle/interception outcome filters and recovery-failure exclusion. Per90 uses compatible supported numerator/exposure scope. Missing exposure is not an invented denominator, and measurement is distinct from normalization and membership.

See [implementation or current method](../src/recovery.py),
[the current local application](unified-local-website-integration.md), and
[test inventory/private verification](test-suite-inventory.md).
This summary creates no source attestation, scoring or publication approval.

## Guarded helper reuse

New callers with source-verified selected events should import `recovery_counts` and `add_per90` from `src.metrics.safe_recovery`. The default uses canonical `PLAYER_KEYS`; duplicate UUIDs, unsafe grouping and duplicate exposure keys fail explicitly. For raw event identity resolution use `integrate_recovery` as before. The historical `src.metrics.recovery_coverage` excerpt remains unguarded for contributor reproduction. See [Batch 5 safety and compatibility report](recovery-helper-hardening-report.md).
