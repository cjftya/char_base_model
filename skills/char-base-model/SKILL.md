---
name: char-base-model
description: Prepare a Blender scene for character base modeling using an existing Blender MCP connection and front, back, left, and right orthographic PNG references. Use for Phase 0 setup, calibration, reference locking, and four-view review.
---

# Character base model · Phase 0

1. Read [input requirements](references/input-spec.md) and the [Blender MCP workflow](references/workflow.md). Locate the repository checkout and its configuration.
2. Discover the actual Blender MCP tools. Use a read-only scene query or Python probe to confirm the target scene, Blender version, and available execution and viewport capabilities. Stop if the target is ambiguous or cannot run the setup.
3. Require all four real PNGs and calibrated crown, sole, and centerline anchors. Run the repository's preflight on the Blender host. Stop on missing, unreadable, or invalid inputs.
4. Run the shared Phase 0 script via MCP against the active scene with a fresh output path. Preserve existing scene content and files. Report conflicts rather than taking ownership of unrelated objects.
5. Inspect the four orthographic views, camera alignment, locks, and packed-image persistence using the review checklist. Declare `REFERENCES_READY` only when every check passes. Mark unavailable checks `UNVERIFIED` and report the output and manifest paths.
6. End after Phase 0. The Body and Head collections are prepared for future work. Leave mesh creation and agent orchestration out of this run.
