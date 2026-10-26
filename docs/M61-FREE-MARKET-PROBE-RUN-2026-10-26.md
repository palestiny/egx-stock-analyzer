# M61 bounded no-cost market-data probe — 2026-10-26

This branch triggers the existing `m61-free-market-probe.yml` workflow for a fresh, metadata-only source check across the fixed ten-symbol cohort.

## Safety boundary

- The workflow must not preserve raw price responses.
- Results are candidate diagnostics only and must not be promoted into an accepted M61 dataset.
- The run does not satisfy point-in-time financial evidence, licensing, corporate-action, or immutable-manifest acceptance.
- Preserve only the uploaded metadata report for review; do not claim strategy profitability from this probe.
