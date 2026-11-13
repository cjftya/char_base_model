# Phase 1 version 1 data contracts

All coordinates are finite world metres (+Z up, -Y forward), not normalized body
ratios. `phase1_contract.validate_contract` is the executable validator. This
format intentionally does not include a default character: the agent must
measure the user's **current** references.

## model_contract.json

| Key | Required content |
| --- | --- |
| schema_version | Integer `1` |
| height_m | Original Phase 0 `character_height_m` |
| axes | `{"up":"+Z","front":"-Y","sole_z":0}` |
| neck | `center: [x,y,z]`, positive `width_m`, `depth_m`; shared Body/Head contact |
| body | `torso`, `limbs`, `source_notes`, `bounds` |
| head (optional until Body Shape Gate) | `rings`, `features`, `nose_vertices`, `nose_base`, `source_notes`, `bounds` |

A ring is `[[x,y,z], ...]` with at least four ordered samples. A loft is
`[ring, ring, ...]` with at least two equally sized rings. Samples are not forced
to be elliptical. A region's `bounds` is `[[min_x,max_x],[min_y,max_y],[min_z,max_z]]`.
`source_notes` explains the source rows/views, uncertainties and reconstruction.

`body.torso` is a loft. `body.limbs` is an ordered list of exactly four branch
objects, one for each `arm_left`, `arm_right`, `leg_left`, `leg_right`. Each
contains `region`, `patch_faces: [integer, ...]` and `rings: loft`. Include simple
hands and feet in the distal limb profiles. Select the host face indices from
the current mesh **after** previous attachments, not from the original torso.
Use a connected disk face patch whose boundary length equals a limb ring's
sample count. Patches cannot be disconnected, contain holes or overlap previous
junctions. The Builder bridges the hole to the limb and closes its distal end.

`head.rings` is the measured skull loft including facial projection. Five
`head.features` objects have the same branch format and exact regions
`eye_left`, `eye_right`, `mouth`, `ear_left`, `ear_right`. Their concentric rings
form integrated eyelid/socket, lip/oral and ear surfaces. At least two feature
rings are required; enough samples must be supplied to preserve the drawing's
actual oval shape. `nose_vertices` identifies three or more vertices in the
constructed mesh **before unused-vertex compaction**; `nose_base` locates the
measured base, and the nose must protrude in -Y beyond it. Numbers are not
quality criteria: Reviewer inspects the resulting anatomy.

Use `Mesh`, `loft`, `boundary`, `remove_patch` to explore face indexing and export
previews via the host's MCP before finalizing the contract. Do not copy the
synthetic test fixture's proportions or patch indices into a real character.

## landmarks.json

| Key | Required content |
| --- | --- |
| schema_version | `1` |
| source_hashes | Exact `{front: sha256, back: sha256, left: sha256, right: sha256}` from session state |
| inconsistencies | Array of cross-view findings, each with `resolved: true` and resolution notes before acceptance |
| views | Exactly the four source directions, each with landmark observations and direction checks |

Each view includes boolean `mirrored`, string `direction_evidence`, and all of
`crown`, `chin`, `neck`, `shoulder`, `chest`, `waist`, `pelvis`, `buttock`,
`elbow`, `wrist`, `knee`, `ankle`, `toe`. Each landmark is an object with
`world: [x,y,z]`, `confidence: measured|estimated|uncertain`, and string `note`.
An invisible axis is estimated from another view and explained in `note`.
Left/right paired measurements may be stored in additional fields; do not hide
asymmetry by recording an unqualified mean.

## state, reviews and attempts

`state.json` records ordered gate state, ACTIVE/COMPLETE/REPLAN/BLOCKED status,
source hashes, contract and landmark hashes, full review history and per-gate
rework counts. Never edit it to bypass a gate. Each attempt binds the candidate
blend, metrics, four renders, two obliques, four overlays, projection metadata
and input contract fingerprints. Reviewer copies the full binding into its
review file. See the skill's `phase1-review.md` for the finding/check format.

The session contains the original draft-independent accepted JSON files,
`phase1_working.blend`, `attempts/*.blend`, `review/attempt_NNN/*`,
`phase0_source/inputs.json` and `scene_snapshot.json`, numbered reports and,
only after final approval, `phase1_final.blend`. Sources stay at their original
paths; current four images are also copied into `references`. No backup folder
is searched automatically.


Checkpoint-backed sessions store the canonical model filename and SHA-256 in
`state.json.checkpoint`. The generation model and candidate state are published
as one logical commit. `head_spec.json` and `head_spec_sha256` bind deferred head
geometry; the shared model contract and approved body specification stay intact.
Evidence includes the generation and optional head-spec hash in review_context.
New meshes store semantic_face_map keyed by polygon vertex membership; the old
positional semantic_regions property is compatibility metadata only.


## Polygon policy

Optional `model_contract.json.polygon_policy` overrides are validated by
`phase1_budget.policy`; see `config/polygon_policy.json` for the single source
of defaults and [budget behavior](../docs/phase1-polygon-budget.md).
Every non-default override requires `exception_reason`. Keep the accepted contract
immutable; policy changes require replanning. Record a dynamic region density
plan in `body.source_notes` and `head.source_notes` before generating samples.
Reference resemblance and joint/facial loops take priority over filling a budget.


## Optional Body junction and section fields

A limb may add `transition_rings` (explicit rings before `rings`) and a nonempty
`transition_note`. Combined rings share one sample count and one density limit.
At least two ordinary rings remain required. `boundary_offset` is a zero-based
cyclic offset applied to every ring in the limb; it requires `mapping_note`.
The constructor never reverses or mirrors samples automatically. Invalid local
winding/folds/crossings block generation even with an explicit offset.

`body.measured_sections` is an array of `{region, ring_index, note, views}`.
Region is torso or a named limb; `ring_index` addresses ordinary rings, excluding
transitions. `views` has front/back/left/right, each `{min, max, z}` in world
metres. Front/back measure X, left/right measure Y. Preserve each direction and
each leg separately, including disagreements; no mean or inferred symmetry.
`phase1_analysis.measure_section` converts calibrated pixel spans to this format.
`section_errors` compares a supplied ring before/after changes; these are sample
extents and do not prove a complete silhouette or exact plane-surface section.

Review findings optionally include `change_type: position|topology`. Existing
findings default to position. Topology REWORK escalates immediately to REPLAN.
`phase1_replan.prepare_replan` creates a new session with unaccepted `drafts/`,
read-only `parent_snapshot/` copies and `replan.json` source/parent fingerprints.
The failed session is never modified; the new run restarts every gate.
