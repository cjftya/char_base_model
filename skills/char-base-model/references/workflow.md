# Blender MCP workflow

## Connect and check

Discover the connected tools by capability. Use scene inspection or read-only Python to get the Blender version, current scene name/file path, host OS, and home path. Confirm Python execution and identify any viewport capture tool. If unavailable, explain the failing capability and guide the user to open Blender, enable/start the installed MCP add-on's connection, check their CLI's MCP configuration, reconnect, and repeat the scene query. Use the installed add-on's actual settings. Keep this MCP workflow blocked until it works.

Keep the repository/harness separate from run data. Transfer folder inputs or attachments to the Blender host through an available supported transfer mechanism. If file transfer is unavailable, ask the user to save the four named files on that host and provide the folder path. Explain which files or paths are inaccessible. Never treat cloud paths as Blender-host paths.

## Create the run directory

Call the helper below through the discovered Python tool. Use absolute paths in the Blender host's native syntax. The helper accepts either a folder or four paths and supports PNG/JPG/JPEG. Safely encode paths in generated Python.

```python
import json
import runpy
import sys
from pathlib import Path

root = Path("/absolute/blender-host/char_base_model")
sys.path.insert(0, str(root / "scripts"))
try:
    intake = runpy.run_path(str(root / "scripts/prepare_session.py"))
    session = intake["prepare_session"](
        ["/absolute/blender-host/input-images"],
        # destination="/absolute/user-requested/location",
    )
    print(json.dumps(session))
finally:
    sys.path.pop(0)
```

Use the explicitly requested destination as the parent directory when present. Resolve “here” against the directory the user identified on the Blender host. If omitted, the helper resolves Windows Downloads using its redirected user-folder registry value, or Linux Downloads using `XDG_CONFIG_HOME/user-dirs.dirs` with `XDG_DOWNLOAD_DIR`. Linux falls back to an existing `~/Downloads`. If unavailable or disabled, ask for the actual destination. A custom destination must already exist and be accessible on the Blender host. Use `destination=...` to supply it.

A run uses host-local time and creates this folder under that parent:

```text
char_base_YYYYMMDD_HHMMSS/
├── references/                   four copied source images
├── config/reference_setup.json   per-run anchors and settings
├── reference_stage.blend
└── reference_stage.manifest.json
```

The timestamp directory is created exclusively. If another run already occupies the same second, retry with a fresh timestamp. All originals remain in their input location. Missing files, unsupported formats, duplicate directions, and images below the intake resolution threshold block staging with a correction message. Inconsistent resolutions produce guidance. Present that guidance to the user before inspecting the images.

## Calibrate and set up the active scene

Inspect the staged images and update their anchors and `anchors_reviewed` in the session config. The agent handles the configuration. Ask the user for clarification only when the image itself or an unavailable inspection capability leaves the anchors or direction ambiguous. Check actual character proportions and pose even if all pixel dimensions match.

After calibration, execute this through the discovered Python tool using the paths returned above:

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
        "/absolute/char_base_YYYYMMDD_HHMMSS/config/reference_setup.json",
        "/absolute/char_base_YYYYMMDD_HHMMSS/reference_stage.blend",
    )
    print(json.dumps(manifest))
finally:
    sys.path.pop(0)
```

The setup rechecks host paths and decodes/packs all four images before replacing existing references. Report decode failures and ask the user to re-export or replace the affected source. Reserved names occupied by unrelated or shared content block setup. Use a fresh output path on a save retry. If saving fails after setup, the active scene may already contain updated references.

## Review and finish

- Inspect Front, Back, Left, and Right Orthographic in Blender. Enable viewport overlays and show Empties when needed. For each direction, verify the intended PNG is visible, reads upright, matches the source orientation, and does not appear in the opposite view. Use asymmetric source landmarks to check mirroring. If the source itself is ambiguous, mark the orientation unverified.
- Verify the sole, crown, and centerline against world coordinates and confirm relative scale and aspect. Check that the reference collection and reference objects resist selection and that transform locks are enabled. Check the four orthographic cameras and the two separate work collections. To use a review camera, assign it in a review viewport or in the saved copy.
- Open the saved copy in a separate Blender session or after the user has safely preserved their open work. Confirm all four images are still packed and visible. Keep the active source scene open during automated setup.
- The script records `UNVERIFIED` in the manifest because it cannot attest to viewport review. Update the per-view `visual_review` and `reopen_review` with `PASS` only for observed checks. Set the manifest status and report `REFERENCES_READY` only when the full checklist passes. Report failed checks with evidence and leave unavailable checks `UNVERIFIED`.
- Reference Empties are viewport guides. Future rendered comparisons use camera-aligned model renders composited separately against the source PNGs.
