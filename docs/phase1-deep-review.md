# Phase 1 extended structural review

## Scope and evidence

Read the complete Phase 1 workflow, contracts/session preparation, geometry
constructors, Blender adapter, compositing, and existing regression tests.
Traced Phase 0 handoff, initialization, both builders, local edits, review
collection/submission and final publication, including interruption points.
No actual Blender execution was performed; host testing belongs to the user.
This is a broader code-path review, not proof of visual or Blender API correctness.

## Corrected defects

| Area | Defect | Correction / verification |
| --- | --- | --- |
| Review freshness | Bindings did not identify stage/history revision | Hash-bound review_context records stage, review count and both input hashes; stale-stage and stale-rework tests |
| Evidence completeness | Missing required views could be omitted from binding | Require candidate, metrics, alignment, context, four views, two obliques and four overlays |
| Evidence paths | Cross-platform separators and symlink artifacts not consistently rejected | Local filename and real-file guards |
| Findings | Arbitrary severity strings could bypass unresolved error check | Validate severity enum, nonempty fields, attempt and preserve-region types |
| Immutable JSON | Serialization failure created a partial file that blocked retry | Serialize before exclusive creation, clean newly created file on write exception |
| Landmark acceptance / findings | Partial publication made identical retry fail | ensure_json accepts identical existing content and refuses differing content |
| Local edits | Documented world coordinates assigned directly to local vertices | Apply inverse object world matrix; actual Blender transform test still needed |
| Ownership | Shared meshes could modify unrelated users of the same mesh | Reject shared/linked data and objects outside their assigned workspace |
| Evidence attempt numbering | Directory count reused an existing number after deletions | Use highest numeric attempt plus one |
| Geometry patch | Boundary-only check could miss disconnected closed components | Check connectivity, edge multiplicity and disk Euler characteristic |
| Nose / bounds | Repeated nose IDs and infinite workspace bounds accepted | Reject duplicate IDs and nonfinite bounds |

78 unit tests pass: previous 65 plus 13 adversarial regression cases. Tests cover
missing views, stale stage/history, changed evidence, omitted landmark hash,
Windows-style traversal, invalid immutable serialization, identical retry,
infinite bounds, repeated nose vertices, disk plus closed component and invalid
severity. Blender ownership and matrix changes remain host-integration checks.

## Remaining structural issues, ranked

### High: checkpoints and state are not one transaction

build_region saves an attempt, replaces working, then publishes state. If state
publication fails, its exception handler removes the in-memory mesh but the disk
working copy can already contain it. Fixed attempt names also obstruct retries.
refine_topology and final review have similar multi-file interruption windows.
Final save can leave phase1_final.blend without a COMPLETE state; it must never
be interpreted as approval by filename alone. Identical JSON retries improve
some failure paths but do not solve these transactions.

Recommended next design: immutable generation checkpoints plus a single atomic
commit manifest selecting the checkpoint and state; a recovery entry point must
reopen that generation through Blender and verify source/mesh fingerprints.
Avoid ad-hoc rollback that can silently discard unsaved user edits. This needs
mock fault injection at each publication boundary and real Blender restart
validation before adoption. Not implemented or claimed resolved here.

### Medium: all detailed geometry required before Body Shape review

accept_landmarks validates and constructs both body and head before body work.
This forces detailed head rings and patch indices upfront, although the intended
process is body review followed by head refinement. It also constructs geometry
twice (validation then Blender building). Split shared measurements/neck contract
from versioned per-builder geometry specifications in a follow-up. Existing
contracts remain compatible in this change; no silent schema migration.

### Medium: topology editing is structurally limited

Explicit evolving face indices make attachment specifications brittle. Region
labels are stored separately from polygons and depend on ordering. Count checks
cannot detect a same-count reordering. edit_region can change positions but not
add loops or restructure a faulty joint. refine_topology recalculates normals;
it is not a retopology implementation. Prefer mesh face attributes/stable region
identities and a controlled topology revision API, validated in Blender.

### Medium: physical/anatomical correctness still relies on review

Closed/manifold counters and nose projection do not prove anatomical shape,
absence of self-intersections, neck contact, hand/foot fidelity or likeness.
Shared neck dimensions are recorded but not quantitatively fitted to both
surfaces. Keep those checks explicit; do not invent universal numeric thresholds.

### Performance and lifecycle

Every context check hashes all original files including the blend, plus packed
image bytes. This favors strict detection but may be expensive for large files.
Overlay processing is Python per-pixel and retains three RGBA buffers; at 4K
this can dominate runtime/memory. Profile the actual host before adding caching
or an optional vectorized compositor; avoid weakening content verification via
mtime-only caches. report() also reads the current scene without proving it is
the target session, so use it only while the correct working file is open.

## Delivery

Changes are committed locally. Remote publication was not retried after the
previous automatic approval rejection. The earlier maintenance commit and this
extended review/fix remain subject to explicit publication approval.
