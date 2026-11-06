# Blender MCP workflow

## Connect and check

Discover the connected tools by capability. Use scene inspection or read-only Python to get the Blender version, current scene name and file path. Confirm Python execution is available and identify any viewport capture tool. If execution is unavailable, report the block and point to the optional offline command in the repository README.

Place the repository and four PNGs where Blender can read them. A CLI-host preflight is useful when files are shared. Always check on the Blender host too. Use absolute Blender-host paths in the following Python snippets. Use the host's path syntax and safely encode any paths provided by the user.

## Run in the active scene

Use the discovered Python execution tool. First run the preflight with this snippet:

```python
import sys
from pathlib import Path

root = Path("/absolute/blender-host/char_base_model")
sys.path.insert(0, str(root / "scripts"))
try:
    from reference_common import load_references
    config, views = load_references(root / "config/reference_setup.json")
    print({name: (view.width_px, view.height_px) for name, view in views.items()})
finally:
    sys.path.pop(0)
```

After that passes, run the setup. Substitute a fresh output path. The script repeats the file checks and decodes and packs all four images before replacing any existing references.

```python
import json
import runpy
import sys
from pathlib import Path

root = Path("/absolute/blender-host/char_base_model")
sys.path.insert(0, str(root / "scripts"))
try:
    setup = runpy.run_path(str(root / "scripts/setup_references.py"))
    manifest = setup["prepare_phase0"](
        root / "config/reference_setup.json",
        root / "output/reference_stage.blend",
    )
    print(json.dumps(manifest))
finally:
    sys.path.pop(0)
```

The setup keeps Body and Head content and adds or refreshes owned references and cameras. If a reserved name is occupied by unrelated content or a managed ID is shared, report the collision. The script saves a separate copy and a sibling manifest. Use a fresh output filename on each MCP rerun. If saving fails after scene setup, the scene may already contain the new references. Retry with a fresh writable destination after resolving the error.

## Review and finish

- Inspect Front, Back, Left, and Right Orthographic in Blender. Enable viewport overlays and show Empties when needed. For each direction, verify the intended PNG is visible, reads upright, matches the source orientation, and does not appear in the opposite view. Use asymmetric source landmarks to check mirroring. If the source itself is ambiguous, mark the orientation unverified.
- Verify the sole, crown, and centerline against world coordinates and confirm relative scale and aspect. Check that the reference collection and reference objects resist selection and that transform locks are enabled. Check the four orthographic cameras and the two separate work collections. To use a review camera, assign it in a review viewport or in the saved copy.
- Open the saved copy in a separate Blender session or after the user has safely preserved their open work. Confirm all four images are still packed and visible. Keep the active source scene open during automated setup.
- The script records `UNVERIFIED` in the manifest because it cannot attest to viewport review. Update the per-view `visual_review` and `reopen_review` with `PASS` only for observed checks. Set the manifest status and report `REFERENCES_READY` only when the full checklist passes. Report failed checks with evidence and leave unavailable checks `UNVERIFIED`.
- Reference Empties are viewport guides. Future rendered comparisons use camera-aligned model renders composited separately against the source PNGs.
