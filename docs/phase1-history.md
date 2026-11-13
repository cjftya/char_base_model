# Phase 1 engineering history (consolidated)

Past implementation reviews are collected here so the active guides focus on the **current** code and test process. For complete historical wording, use Git history (before the consolidation commit). Historical test counts are not current suite results.

## Maintenance refactor — 65 recorded tests

- Separated workflow state transitions (`phase1_workflow`) and reference compositing (`phase1_render`) from Blender orchestration.
- Improved atomic state JSON replacement, local edit face lookup, semantic label checks, contract/landmark hash binding and evidence path validation.
- Known at the time: split model/state publication, synchronous rendering and relatively expensive per-pixel overlays. The publication issue was subsequently addressed by immutable checkpoints.

## Extended structural review — 78 recorded tests

- Tightened review freshness/completeness, path safety, typed findings, nonfinite bounds and nose sample checks.
- Fixed immutable JSON retry, local/world coordinate conversion, mesh ownership checks, attempt numbering and attachment disk validation.
- Flagged missing atomic checkpoint/state selection, premature Head specification, brittle face-order labels and incomplete physical likeness checks. The first three were subsequently addressed.

## Structural follow-up — 89 recorded tests

- Added immutable Blender generations and an atomic `state.json` checkpoint selection, with explicit recovery and interrupted-writer lock detection.
- Deferred Head geometry until Body Shape approval and changed region identity to face vertex membership instead of polygon index.
- Reports now refuse unrelated/stale working scenes. Power-loss durability and real Blender save/reopen remained host-validation items.

## Subsequent budget and midpoly revisions

- Evaluated-triangle budget and review gates: originally **98** recorded unit tests. The policy has a 30,000 triangle maximum and a warning at 24,000.
- Midpoly changes: **119** recorded unit tests and a Blender 4.3.2 synthetic smoke test. Added transition rings, explicit cyclic correspondence, fold/crossing diagnostics, four-view section measurements and new-session REPLAN lineage.
- These changes do not implement fully automatic retopology, prove reference likeness, or certify global self-intersection freedom.

## Current documentation

- [Implementation and real-test status](phase1-validation.md)
- [Polygon policy and review gates](phase1-polygon-budget.md)
- [Midpoly implementation and retest procedure](phase1-midpoly-review.md)
- [Executable modeling workflow](../skills/char-base-model/references/phase1-modeling.md)
