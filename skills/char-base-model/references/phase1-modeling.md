# Phase 1: measured character construction

## Entry and capabilities

Use the user's current Phase 0 session, never a guessed latest directory or any
`backup*` input. Preserve the existing Phase 0 scripts and manifest. Discover the
connected Blender MCP's actual scene query, Python, image observation, open and
save tools. Record tool names, observed Blender host/version, and capability
results. Never start another MCP server. If required capabilities are absent,
report `BLOCKED`; code development/tests can continue, but do not claim a model
or Blender test succeeded. Prefer Blender 5.x; feature-test APIs on other versions.

All Python operations below run **on the Blender host**, with the repository's
`scripts` directory on `sys.path`. A cloud attachment path is not automatically
a Blender-host path. Keep the harness in the repository. Keep generated data in
the new session. No automatic script modifies Phase 0.

## Establish the working copy

1. Inspect current scene/file and unsaved user edits. Open the explicitly chosen
   Phase 0 source with the user's existing MCP tools only after preserving edits.
2. Complete Phase 0's existing image, lock, alignment, packed and reopen checks.
   Do not modify its manifest's UNVERIFIED fields just to pass this phase.
3. Create a **separate** `phase0_review.json` containing `blend_sha256`,
   `manifest_sha256` (from `phase1_contract.digest`), and `front`, `back`, `left`,
   `right`, `locks`, `alignment`, `packed`, `reopen`, each `PASS` only after actual
   observation. Record reviewer/evidence notes too. Missing checks block entry.
4. Invoke `phase1_contract.prepare_session(source_blend, manifest, phase0_review,
   destination=...)`. Inputs must be absolute existing paths. An explicit
   destination is the **exact new output directory**, whose parent must exist;
   omit it to use host Downloads/char_base_YYYYMMDD_HHMMSS. Existing output,
   timestamp collisions, input errors and inaccessible Downloads stop the call.
5. Invoke `phase1_blender.initialize_working(session)` from the clean, open
   source. It verifies packed bytes against input hashes, remaps dependencies
   into the working copy, opens it and snapshots protected objects. Never skip
   this step or manually save over the source. This phase only replaces its own
   `phase1_working.blend`; attempts/final files are exclusively created.

## Plan polygon density before generation

Read [polygon policy and failure handling](../../../docs/phase1-polygon-budget.md).
Load effective values with `phase1_budget.policy`; never duplicate numeric defaults
in prompts. Record a dynamic density plan in Body/Head `source_notes` before
supplying rings: prioritize measured face contours and joint loops, use fewer
samples along straight/flat spans, and explain uncertainty. Treat the target
range as guidance, not a minimum or a fixed per-part quota. A policy override
belongs in the draft contract with `exception_reason` before acceptance.

After generation inspect actual original/evaluated counts and object/region
rankings. Preserve existing modifier/duplicate-object restrictions. Never apply
blanket Decimate, subdivision or remesh. If unnecessary loops require topology
changes beyond local vertex edits, stop and replan a separate session preserving
the current one. Stop reduction if reference shape or joint loops would suffer.

## Measure, then create the contract

Inspect all four originals at useful resolution. For each view record crown,
chin, neck, shoulder, chest, waist, pelvis, buttock, elbow, wrist, knee, ankle and
toe. Use `phase1_analysis.pixel_to_world(ReferenceView, x_px, y_px,
hidden_axis=...)` with **the original Phase 0 calibration**. It returns world
metres, with +Z up and -Y character front. The invisible axis is an explicit
estimate, not evidence from that view. Record source notes, confidence
(`measured`, `estimated`, `uncertain`), mirror/direction evidence and unresolved
contradictions. Resolve contradictory poses/shapes explicitly; never average
away inconsistent anatomy. Hair/horns/tail/accessories are excluded. If an
occluded silhouette cannot be supported, mark uncertainty or block that region.

The initial contract may omit `head`; retain shared height, neck and landmark measurements. After Body Shape Gate, call `accept_head(session, head_spec_path)` to validate and bind the measured head specification. Existing contracts containing both regions remain supported.

Write two draft files outside their eventual session filenames, then invoke
`accept_landmarks(session, draft_contract, draft_landmarks)`. See
[contracts](../../../contracts/phase1-format.md) for the exact structure.
The accepted copies are immutable for the session. Change the contract only by
starting a new, explicitly replanned session. Local vertex corrections use
`edit_region` and remain recorded alongside the original measurements.

### Body construction

- Supply explicit rings sampled from the images, ordered consistently around
  their centreline. Sample X width from front/back and Y depth/centre shift from
  left/right. Use non-elliptical/asymmetric samples when the drawings support
  them. Do not substitute generic human/chibi proportions or fixed circles.
- Torso rings run pelvis to neck. Limb rings follow shoulder/elbow/wrist or
  hip/knee/ankle. Distal rings describe simple hands/feet and must include actual
  toe/heel and palm volume; no shoes, detailed fingers or rigging in this phase.
- A limb replaces a contiguous disk patch of torso faces. `patch_faces` refers
  to the **current** torso/previously attached mesh. For multi-face patches,
  inspect boundary orientation with `phase1_geometry.boundary`.
- A 2x2 quad patch has eight boundary vertices; a 3x3 patch has twelve. Use equal
  sample counts on the limb's first ring. Begin near the host patch and continue
  along the measured centreline. Keep boundary ordering consistent, avoiding
  twists. The constructor bridges the boundaries into **one surface** and
  removes orphaned interior patch vertices. This is real mesh connectivity,
  not a Boolean union or primitive overlap.
- Choose shoulder/underarm and bilateral hip/crotch patches with care. The helper
  cannot determine an anatomical junction from arbitrary face numbers. If a
  junction pinches or self-intersects, Reviewer must return REWORK/REPLAN.
- Use enough samples for measured shape, within the 30,000 evaluated-triangle
  total limit. Body/Head allocations of roughly 8,000–12,000 each are optional
  planning references, never minimums. All dimensions come from the measured contract.

Invoke `build_region(session, 'body')`. Observe the actual mesh, run
`collect_evidence`, and pass Body Shape Gate before building Head.

### Head construction

- Supply ascending skull rings matching forehead, temple, cheeks, chin and
  occiput in both front and side views. Include nose bridge/tip/alar shape in
  these **integrated** 3D samples; identify at least three `nose_vertices` and
  the measured `nose_base` on the forward -Y surface.
- Replace distinct skull disk patches with concentric measured rings for
  `eye_left`, `eye_right`, `mouth`, `ear_left`, `ear_right`. Eye rings represent
  eyelid rim, inner rim and recessed socket; mouth rings represent lip/oral
  inset, and ears extend laterally. Rings close into the same connected surface.
  Keep eye and mouth loops oval and sufficiently sampled; a rectangular inset
  that does not resemble the drawing is a failed visual gate.
- At least two rings per feature are required. Use more to retain rim shape;
  no texture/flat decals can replace geometry. Nose projection validation is
  necessary but **not sufficient** for anatomical likeness.
- Match the shared neck centre/width/depth, height and workspace bounds. Body
  and head remain separate closed meshes, with neck contact verified visually.
  They are not advertised as rig-ready.

Invoke `build_region(session, 'head')` only after Body Shape Gate. Obtain a Head
Shape review before `refine_topology(session)`. The refinement retains measured
ring loops and recalculates normals through BMesh. It does **not** perform a
magical retopology pass: major loop changes require explicit replanning, and
local shape fixes use the bounded rework path. Voxel/quad remesh, if used manually
in a separately planned workflow, is only intermediate geometry.

## Review, local correction and persistence

Invoke `collect_evidence(session)` after each model/edit stage. It saves a working
checkpoint, creates a never-overwritten attempt directory and candidate blend,
renders four Phase 0 cameras plus front/back 3/4 views in an isolated review
scene, and produces four overlays and projection metadata. Read
[review rules](phase1-review.md) before judging any artifact.

Have a separate read-only Reviewer inspect the actual candidate file, images,
metrics and overlays. A separate agent can perform this role; when agents are
unavailable, execute the same role sequentially with no Builder edits during
review and disclose the lack of independent-agent review.

Submit the resulting file with `submit_review(session, evidence_folder,
review_path)`. On REWORK, invoke `edit_region(session, 'body' or 'head', edits)`
where `edits` maps vertex index to a new world coordinate. These generated meshes
have identity transforms. Identify affected semantic face/vertex indices using
`semantic_regions` on the object. Changes must belong to the named findings and
must avoid `preserve_regions`. Rework is also available at integration gates.
Never regenerate an approved region to correct an unrelated issue. Collect
**fresh evidence** and ask Reviewer again. Two reworks per gate are allowed;
a third failure halts at REPLAN. BLOCKED and REPLAN require a newly planned
session. No endless retries or forced state JSON edits.

After both shape gates, refine loops/normals, collect evidence, and review
integration. A final evidence/review step writes `phase1_final.blend` only on
PHASE1_COMPLETE. `report(session)` creates a numbered report including gate
history and actual mesh counts. Report unresolved likeness, self-intersection,
neck gaps and unavailable measurements explicitly. An I/O interruption between
checkpoint and state publication is a recovery situation: inspect the saved
attempt, report the interruption, and replan if consistency is uncertain.

## Committed generations and recovery

Every successful model/state operation publishes an immutable
`phase1_generation_<id>.blend` beside the working file, then atomically selects
it in `state.json.checkpoint`. Only this state-selected generation is committed.
Unreferenced generations are failed attempts and must not be selected by date.
The Blender scene carries the same generation identifier; reopening a stale
working file blocks operations until recovery.

Use `recover_working(session)` to verify the committed hash, recreate the working
file and reopen it. Unsaved scene edits stop recovery; preserve them separately
before calling again, or explicitly authorize `discard_unsaved=True`. On a
committed COMPLETE state this also recreates a missing final output. The final
filename alone is not evidence of approval. A publication lock prevents two
writers. After process termination, confirm no writer remains before removing
`.checkpoint.lock`; never clear another live writer's lock automatically.

The working file is now a recoverable convenience copy, not the authoritative
checkpoint. Existing Phase 1 sessions without checkpoints/face maps must be
replanned in a new session from their original Phase 0 inputs; no automatic
migration guesses which old file was approved. Phase 0 inputs remain unchanged.
Polygon region lookup tolerates polygon reordering and winding reversal. A
changed vertex membership is a topology revision and deliberately blocks local
position edits. Major retopology still needs explicit replanning.


## Junction measurement and explicit REPLAN

For shoulders and hips, inspect the deleted patch boundary and root-ring
correspondence with `phase1_junction.correspondence(host_points, root_points)`.
The report includes the nearest cyclic offset, bridge lengths, reversed winding,
folded quads and crossing bridge edges. Nothing is auto-mirrored or reversed.
Fix the draft ring order or explicitly supply `boundary_offset` plus `mapping_note`;
the offset rotates **all** transition and limb rings together. A non-nearest
mapping requires a documented explicit choice, and still cannot bypass fold,
winding, collapsed-edge or crossing checks. These are conservative local tests,
not proof of global self-intersection freedom or smooth anatomical flow.

Optional limb `transition_rings` precede `rings` and require `transition_note`
identifying image rows, contour/depth observations and intended improvement.
Supply explicit nonuniform measured coordinates; there is no automatic
interpolation/smoothing. All rings in this branch must have the same sample
count as its host boundary; transitions plus ordinary rings share the existing
128-ring ceiling. Keep at least two ordinary limb rings. Recompute evolving
`patch_faces` after topology changes. Patches must only select remaining torso
faces, never previously attached limbs or junctions.

Measure waist/pelvis/thigh/knee/calf/ankle spans separately for both legs.
`phase1_analysis.measure_section(views, observations, region=..., ring_index=...,
note=...)` accepts four calibrated `[left_px, right_px, row_px]` observations.
Use actual camera directions for `views`, retaining original filename mapping
in direction evidence (including left/right filename swaps if observed).
Store results in optional `body.measured_sections`; ring indices refer to
ordinary `rings` (or `torso`) and exclude transition rings. Compare
`section_errors(section, ring)` before/after changes for per-view width/depth,
height and perimeter errors. It compares sample extents, not an exact plane
intersection. Do not average opposing views or mirror one leg to fill the other.
Reject unsupported added loops: compare four silhouettes, section errors,
bridge defects and six-view appearance; retain extra density only with a
measured benefit. `planned_sections` in metrics describes the accepted plan,
not later edited geometry; take fresh measurements after local edits.

A finding needing a new patch, ring count or connectivity uses
`change_type: "topology"` and verdict REPLAN. A topology finding submitted as
REWORK is escalated to REPLAN without spending position-edit retries.
`change_type: "position"` (legacy default) keeps the existing two-rework limit.

From a halted session call:

```python
from phase1_replan import prepare_replan
new_session = prepare_replan(
    failed_session, revised_contract_path, revised_landmarks_path,
    reason="Measured hip/shoulder junction redesign", destination=new_absolute_folder)
```

This verifies parent sources, accepted hashes and committed checkpoint, preserves
all parent files, and creates a fresh REFERENCES_READY session from original
Phase 0. It writes `replan.json` lineage, `parent_snapshot/`, and `drafts/` files;
it accepts no landmarks and inherits no review PASS. Missing/legacy checkpoint
or altered source blocks this helper; preserve the old artifacts and use the
normal Phase 0 entry workflow explicitly instead of editing old state.
Preserve unsaved edits, open the original Phase 0 source through MCP, run
`initialize_working(new_session)`, then `accept_landmarks(new_session,
new_session/'drafts/model_contract.json', new_session/'drafts/landmarks.json')`.
Build Body and collect a fresh shape review. Only after Body PASS accept/build
Head. Keep old/new overlays for comparison; never relabel the failed run COMPLETE.
