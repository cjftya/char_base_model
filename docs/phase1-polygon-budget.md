# Phase 1 polygon budget

## Policy and planning

`config/polygon_policy.json` is the single source of defaults. Call
`phase1_budget.policy(contract.get('polygon_policy'))` to obtain effective values.
The optional contract field accepts partial overrides and requires a nonempty
`exception_reason` for changes. Never silently modify accepted contract files.

The default reference range is 16,000–24,000 triangles; it is not a minimum. Warn at 80% of the maximum; exactly the maximum
remains acceptable with warning, above it blocks PASS. Ring sample and ring count
limits are each 128 per loft: generous safety ceilings for measured lofts,
not suggested densities or per-part allocations. They are configurable with a reason.

Before creating the contract, describe a dynamic allocation in region
`source_notes`: identify silhouette changes, facial contours and joint loops;
explain where more samples are necessary and where straight/flat spans can use
fewer. Do not use fixed body-part quotas, add loops just to meet the range, or
change measured proportions to reduce counts. Existing builders use explicit
lofts/branches rather than primitives, so there is no primitive segment setting.

## Counting and gates

Budget inclusion is the owned character meshes actually used by this pipeline's
review scene. References, cameras, lights and unrelated user meshes are excluded.
Visible separate character meshes must be owned and included; current gates
permit only Body and Head. Additional character objects require an explicit
contract change rather than bypassing ownership. Hidden objects are excluded
from the budget summary but existing session guards reject hidden Builder meshes.

Original and evaluated vertices, edges, faces and triangles are collected per
object. Blender `calc_loop_triangles()` supplies actual tessellation; face count
times two is never used. Pure contract preflight sums `n-2` for valid simple
polygon faces, including n-gon caps; Blender counts are authoritative at review.
Invalid faces still fail mesh-health gates. Reports rank objects by evaluated
triangles, give modifier growth/settings and original semantic-region counts.

The current session contract forbids modifiers, constraints, animation and shape
keys. Thus evaluated geometry is equivalent for viewport/render in supported
sessions. Read-only diagnostics on externally altered meshes collect viewport
evaluation but mark render evaluation unverified and block acceptance. They do
not claim to evaluate differing render subdivision levels. No export is performed;
an exported mesh count remains NOT_EXPORTED. Evaluated temporary data is cleared
even if counting fails.

Contract preflight, Builder publication, topology advancement and Reviewer PASS
enforce the budget. Evidence contains the effective policy and summary; changing
defaults or overrides after evidence collection requires collecting new evidence.
Existing evidence without a budget summary must also be collected again.
Mesh health includes duplicate faces/vertices, isolated vertices, components,
open/nonmanifold edges/vertices and winding. Current Body/Head must be closed;
there are no intentional open boundaries in this contract. Symmetry and whether
a separate part is unnecessary remain explicit manual review items because
cross-view references can contain intentional asymmetry.

## Failure and review

Inspect ranked objects, region counts and modifier diagnostics. First reduce
unnecessary samples/loops in the measured plan or remove unintended external
modifiers. No automatic optimization or geometry-changing fallback is performed.
The existing local rework path only moves vertices; it cannot reduce topology.
If regeneration is needed, use a new replanned session preserving the old one.
Position-only REWORK allows two attempts before REPLAN; findings that require topology changes trigger REPLAN immediately. Stop if
reducing density would damage facial contours, proportions or joint loops.

Independent Reviewer must rerun `validate_scene()` through Blender, compare it
with saved metrics and inspect all overlays, rather than trust Builder claims.
Inspect face contours, neck contact and joint-loop placement at low density too.

Manual test: provide four images → complete Phase 0 checks → generate measured
Body/Head → inspect `metrics.json.polygon_budget` and object counts → compare
front/back/side overlays and face/neck/joints → submit the independent review.
PASS requires acceptable visual checks, mesh health and budget within the limit.

## Verification and limits

Unit and synthetic Blender tests verify limits, tessellation counting, evaluated mesh checks, and stale-evidence blocking. The current commands and status are in [Phase 1 validation](phase1-validation.md).

An in-budget mesh is not automatically anatomically correct. Four-view reference likeness, smooth junctions and global self-intersections still require actual character review.
