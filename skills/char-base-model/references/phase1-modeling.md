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
- Use enough samples for shape first. Do not pre-emptively enforce a low polygon
  cap. All final dimensions come from the measured contract.

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
