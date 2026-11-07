# Phase 1 maintenance review

Review preceded this refactor. Findings and resulting changes:

| Finding | Change |
| --- | --- |
| State rules mixed with filesystem contracts; transition maps duplicated in Blender adapter | Pure phase1_workflow module owns states and stage maps; phase1_contract re-exports existing API for compatibility |
| Pixel compositing mixed into modeling orchestration | phase1_render owns calibrated overlay processing |
| Fixed .pending.json can remain after failure and block retries | Unique sibling temporary file, flush/fsync, atomic replacement and finally cleanup |
| Editing N vertices scans all faces N times | Build requested vertex-to-region associations in one face traversal |
| Semantic labels may become stale after topology changes | Reject mismatched polygon/label counts before editing |
| Review checked contract hash but omitted landmark hash | Validate both bindings and reject non-local evidence filenames |

Validation: 65 automated tests pass, including serialization and publication
failure recovery. Actual Blender execution is left to the user's host testing.

Remaining architectural limits: Blender checkpoint and state JSON publication
are separate transactions, so an interruption between them still requires
recovery inspection. Rendering and review remain synchronous, and the overlay
uses Python pixel loops; actual host profiling should precede optimization.
The builders require measured explicit profiles and are not automatic anatomy
reconstruction. Large topology changes require replanning because face indices
and semantic labels are coupled. These limits are not claimed resolved by this
maintenance refactor.
