---
name: char-base-model
description: Prepare Phase 0 and construct and review Phase 1 body/head base meshes in Blender through an existing Blender MCP connection from a user-provided folder or four attached front/back/left/right PNG or JPEG images. Stage run data in a timestamped directory under the user-specified location or host Downloads, calibrate and lock references, and prepare review cameras.
---

# Character base model · Phase 0 / Phase 1

1. Read [input requirements](references/input-spec.md) and the [Blender MCP workflow](references/workflow.md). Locate the skill's repository scripts.
2. Accept either an image folder or four attached files named `front`, `back`, `left`, `right`, each with a PNG, JPG, or JPEG extension. Inspect for missing views, format errors, low resolution, inconsistent scale/pose, and direction mistakes. Give specific correction guidance and pause when inputs cannot support alignment.
3. Discover the actual Blender MCP tools. Confirm the connected host, scene, version, Python execution, and viewport capabilities. If Blender cannot be reached, guide the user to start Blender, enable its MCP connection, reconnect their CLI, and retry a scene query. Keep the run blocked until the connection works.
4. Make the inputs accessible to Blender using an available transfer capability. If only CLI-local attachments are accessible, ask for their Blender-host folder location. Never assume shared paths. Run `prepare_session.py` on the Blender host with the folder or four paths. A user-specified destination takes priority over Downloads. The session folder is `char_base_YYYYMMDD_HHMMSS`.
5. Inspect the staged images and configure crown, sole, and centerline anchors in the session's config, then set `anchors_reviewed=true`. Report resolution differences and resolve ambiguous pose/direction before proceeding. When image inspection is unavailable, guide the user to supply the missing information.
6. Execute the shared Phase 0 setup through MCP using the returned session config/output paths. Preserve unrelated objects and save a separate Blender copy. Keep the skill/harness in its repository and all run data in the session directory.
7. Inspect all four orthographic views, locks, camera alignment, and packed-image persistence. Declare `REFERENCES_READY` only when every check passes. Mark unavailable checks `UNVERIFIED` and report the session path and correction guidance.
8. For Phase 0-only requests, report its outcome and stop. For base-mesh/Phase 1 requests, read [Phase 1 modeling](references/phase1-modeling.md), [Phase 1 review](references/phase1-review.md), and [contract format](../../contracts/phase1-format.md) before executing. Preserve the Phase 0 originals and work only in the new working copy. Follow sequential Body → shape gate → Head → shape gate → topology → integration → final gates. Missing MCP/input or unobservable visual checks block model completion; code tests never replace a likeness review.
9. Give guidance and completion reports in the user’s language. Record actual meshes, six renders, overlays, review findings and gate states. Never force COMPLETE or silently select backup inputs.
