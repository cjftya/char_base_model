# Read-only Phase 1 review

Inspect the candidate's actual mesh through the existing Blender MCP, then the
four orthographic PNGs, two obliques, four overlays, `alignment.json`,
`metrics.json`, accepted contract/landmarks and exact `evidence.json` hashes.
Do not modify mesh, scene, state or report checks you cannot observe.

## Independent polygon validation

Read [polygon policy](../../../docs/phase1-polygon-budget.md). Rerun
`phase1_blender.validate_scene()` on the actual candidate through Blender MCP;
do not trust Builder counts. Compare the result with `metrics.json.meshes` and
inspect `polygon_budget` policy, totals, object ranking and warnings. Missing or
stale budget evidence needs recollection. Over-budget or unverified render
geometry blocks PASS; do not excuse it because original face counts look small.
Inspect duplicate/disconnected parts and reference-supported symmetry manually.
Check facial contours, joint loops and silhouette even when triangle count is low.

## Evidence and verdict

Every review file contains:

```json
{
  "role": "Reviewer",
  "reviewer": "actual reviewer agent/role identifier",
  "verdict": "REWORK",
  "evidence": {"copy": "the complete contents of this attempt's evidence.json"},
  "checks": {
    "proportions": "PASS",
    "silhouette": "REWORK",
    "volume": "PASS",
    "connections": "PASS",
    "mesh_validity": "PASS"
  },
  "findings": [{
    "region": "torso",
    "severity": "error",
    "evidence": "overlay_front.png, waist rows",
    "expected": "reference waist outline",
    "observed": "candidate waist extends beyond both sides",
    "suggested_action": "narrow only the waist ring samples",
    "preserve_regions": ["arm_left", "arm_right"],
    "attempt": 1
  }]
}
```

Replace the illustrative `evidence` object with the full real binding; never use
these placeholder strings in an actual review. Allowed verdicts are PASS,
REWORK, REPLAN, BLOCKED. Findings must include all shown fields. PASS needs all
five checks observed and PASS, plus no unresolved error/critical findings.
Unavailable visual evidence is UNVERIFIED and cannot support PASS. Use BLOCKED
for unavailable tools/input and REPLAN for a structurally incorrect approach.
The state machine limits each gate to two corrective attempts.

## Shape checks

- Proportions: full height, head/body relationship, shoulder/pelvis widths,
  extremity lengths and landmark positions, separately for each direction.
- Silhouette: compare overlay alignment metadata before judging shape; retain
  the Phase 0 camera scale, pixel aspect, crop, image mirroring and source image
  world transforms. An attractive front render alone is not enough.
- Volume: front/back obliques and both profiles must show skull depth, cheeks,
  jaw, eyelids/socket, integrated protruding nose, lip/oral form and ear depth.
  A sphere with image features is REWORK. Beware flattened faces or coincident
  layers that happen to look correct in front.
- Connections: inspect shoulders, underarms, crotch, hips, knees, elbows and the
  separate head/body neck contact. Reject primitive overlaps, twisted bridges,
  pinching or visible neck gaps. Confirm simple hands and feet have volume.
- Mesh validity: read boundary/nonmanifold/winding/duplicate/isolated/degenerate
  statistics and inspect actual local topology. Zero counters do not prove
  freedom from self-intersection or good facial/joint flow. The automatic
  `self_intersections` field stays UNVERIFIED: inspect cross sections/local
  geometry before asserting that visual check passed. Uninspectable regions
  block PASS. Modifiers, shape keys, animation and hidden builder objects are
  outside this implementation and blocked to avoid stale render evidence.

## Quantitative comparison

`phase1_geometry.silhouette_metrics(reference_mask, model_mask,
alignment_verified=True)` computes IoU, excess/missing pixels and row-width
errors from human-verified binary masks on **the same calibrated canvas**.
False/default alignment, ambiguous background/shadows/clothing, or empty masks
returns UNVERIFIED rather than a made-up score. Store real measurement results
as additional JSON in the attempt before binding/reviewing it. Do not infer
universal PASS thresholds from a synthetic fixture. Record sample-specific
limits, measurement method and uncertainty in the findings.

`phase1_analysis.landmark_errors` retains per-view landmark distances in metres;
compare height-row width/depth errors after converting pixels with the relevant
Phase 0 calibration. Do not pool contradictions. The overlay pipeline performs
visual alignment and nearest-neighbour reference sampling; it does not segment
complex backgrounds or infer anatomical ground truth.

## Final reporting

Report code tests and real Blender/MCP tests separately. Include actual object,
vertex and face counts only from the model that was evaluated. If MCP is absent,
state that no real character blend/render/likeness verdict is available, name the
blocked stage and give connection guidance. Keep synthetic topology tests clearly
separate from a reference-matched character result. List the top 1–3 concrete
remaining improvements and the output paths. Do not label the run COMPLETE just
because unit tests passed.


## Junction and density review

Inspect both hip shelves/crotch transitions and shoulder/underarm flow in four
overlays and both obliques. Compare calf width and knee/ankle transition on each
side; inspect pelvic/thigh depth in both profiles and neck contact after Head.
Use current `junctions`, `folded_quads`, `min_quad_normal_cosine`, and
`region_density` as supporting diagnostics. `planned_junctions` is generation
metadata only; `planned_sections` describes accepted ring samples, not later
local edits. Geometry PASS never replaces these visual checks. The constructor
rejects detected folds/crossings, but coplanar contact, adjacent-face collision,
global self-intersection and anatomical shelves still require visual inspection.

For a patch/ring/connectivity change mark the finding `change_type: "topology"`
and REPLAN; use `position` only for a topology-preserving local edit. A structural
failure should not spend two futile vertex-edit rounds. A sequential self-review
must identify itself as such; do not call it independent-agent validation.
