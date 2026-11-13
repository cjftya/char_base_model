# Phase 1 midpoly / junction review

## Before implementation (base f0c3d03)

- Baseline: 98 unittest tests pass. No Blender/MCP or failed session ZIP is available here.
- Confirmed: `Mesh.bridge` connects matching indices without correspondence or fold diagnostics. Closed/manifold counters alone cannot detect a twisted geometric bridge.
- Confirmed: Body patches are removed by evolving indices, but do not reject selection of a previously attached limb/junction. Existing documentation already forbids that selection.
- Confirmed: REPLAN halts a session; there is no explicit immutable lineage/new-draft helper. Position-only `edit_region` must remain unchanged in scope.
- Confirmed: calibrated point measurement exists, but no per-view width/depth section comparison helper exists.
- Confirmed: evaluated Blender triangle counting, hidden-object guards, evidence freshness, deferred Head and checkpoint publication already exist. Preserve them.
- Reported, not independently reproduced: the previous 5,336-triangle Body has hip shelves, angular shoulders and calf/profile errors. Polygon shortage is not an established root cause.

## Planned changes

Add a small pure junction diagnostic module; validate explicit correspondence and measured transition rings in Body construction. Add per-view section comparisons without symmetry inference. Add a new-session REPLAN helper with source/checkpoint/contract fingerprints and fresh gates. Strengthen geometry health checks before publication and review, retaining read-only diagnostics. Update schema, modeling/review guidance and regression tests. Keep 30,000 maximum / 24,000 warning / 128 ring safety limits; use 16,000–24,000 only as nonbinding guidance.

Self-intersection and resemblance remain UNVERIFIED until actual six-view Blender review. No blanket subdivision, remeshing, automatic smoothing or new state machine.

## Implemented behavior

- `phase1_junction.py`: explicit cyclic-offset analysis, per-quad fold/degeneracy checks and finite 3D bridge-edge crossing detection. Nearest mapping is advisory with an explicit documented override; structural defects are never waived. No automatic reversing/mirroring.
- `phase1_geometry.py`: measured proximal transition rings, torso-only patch selection, preserved same-sample loft contract, current-seam reconstruction and common health rejection. Each limb still requires at least two ordinary rings, independently of transitions.
- `phase1_analysis.py`: calibrated four-view section spans and per-view sample-extents/perimeter error reports. Separate leg regions and source-camera directions remain separate.
- `phase1_replan.py`: new drafts/session from verified original Phase 0 with parent state/contract/checkpoint hashes and snapshot; no parent writes or inherited PASS. Failed new-session publication removes only the newly created directory.
- `phase1_workflow.py`: explicit topology findings escalate REWORK to REPLAN immediately; ordinary position corrections retain the existing two-rework limit.
- `phase1_blender.py`: retain generation diagnostics separately from recomputed current-seam diagnostics; collect actual Blender tessellation counts and region areas/shares/density. Reject observed health failures before local-edit publication and review acceptance.
- Schema, skill references, README and polygon documentation describe these contracts and their limitations. Phase 0 implementation remains unchanged.

The independent code review found and resolved lost runtime junction diagnostics,
missing runtime volume/vertex-manifold rejection, and a transition-ring path that
could bypass the ordinary two-ring minimum. These are code-review results, not
an independent character likeness review.

## Verification (2026-11-13)

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -q` | 119 passed, 0 failed, 0 skipped in this environment |
| `python -m compileall -q scripts tests` | PASS |
| `git diff --check` | PASS |
| `blender --background --factory-startup --python-exit-code 2 --python tests/blender_midpoly_smoke.py` | PASS on Blender 4.3.2; synthetic measured-transition Body and Head, evaluated counts/region diagnostics, collapsed post-edit seam rejection |
| 23,999 / 24,000 / 30,000 / 30,001 triangle boundaries | PASS / WARNING / WARNING / FAIL |
| Default policy | max 30,000; warning 0.8; guidance [16,000, 24,000]; ring sample/count limits 128 unchanged |
| Real four-reference character through Blender MCP | NOT RUN |
| Shoulder/hip shelves, calf/depth likeness, facial likeness and global intersections | UNVERIFIED |

The optional JSON Schema conformance test needs `jsonschema`; it skips when that
package is absent. Production helpers continue to use the standard library
outside Blender. Synthetic Body/Head counts are test fixture sizes, never a
recommended modeling density. No low-end triangle count is itself a failure.

## User retest procedure

1. Update this repository on the Blender host and reconnect the existing MCP.
   Preserve unsaved work and select the current four original references. Do
   not choose backup inputs or rename/flip left/right images by assumption.
2. If continuing the failed checkpoint-backed session, prepare revised contract
   and landmark files, then call `phase1_replan.prepare_replan(...)` as shown in
   the modeling reference. Keep the failed directory intact. If no valid
   checkpoint exists, use the normal new-session Phase 0 path explicitly.
3. Record camera-to-original-file mapping; remeasure each calf/knee/ankle width
   and both pelvic/thigh depths. Supply measured shoulder/hip transitions and
   correspondence notes. Recompute evolving patch indices, and compare section
   errors before/after adding loops; do not fill a target polygon minimum.
4. Open original Phase 0, initialize the new working copy, accept its draft
   landmarks/contract, then build Body. Collect all four overlays and two
   obliques. Inspect both shoulder/underarm and pelvis/crotch/thigh seams for
   shelves, folds and collisions; compare calves and side depths to references.
5. Submit a real Body Shape review. Use position REWORK for a local correction;
   use topology REPLAN for changed ring/patch/connectivity. Only after Body PASS
   accept/build Head and inspect integrated eyes/nose/mouth/chin/ears and neck.
6. Run remaining topology/integration/final gates, checking evaluated aggregate
   triangles, checkpoint hashes and actual output state. Do not claim COMPLETE
   or render/likeness PASS solely from the automated tests above.

## Remaining limits

The local tests are deliberately conservative: they can reject concave/folded
quads and large local direction reversals, requiring measured redesign. They do
not prove tangent continuity, coplanar clearance, global self-intersection freedom
or anatomical likeness. No BVH or general remeshing engine was added. Section
metrics compare supplied ring sample extents rather than intersecting an edited
surface at exact heights; `planned_sections` is explicitly accepted-plan-only.
Visual shelves can persist in a numerically valid mesh and must fail review.
