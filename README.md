# char_base_model

Blender orthographic-reference-first character base modeling experiment.

**Current scope: Phase 0 scaffold.** A real mesh, rig, modeling agents, and automatic visual comparison are **not implemented yet**. The first executable step prepares a clean Blender scene with four reference images already positioned before any modeling starts.

## Inputs

| File | Orthographic view |
| --- | --- |
| `references/front.png` | Front (-Y) |
| `references/back.png` | Back (+Y) |
| `references/left.png` | Left (-X) |
| `references/right.png` | Right (+X) |

Prepare all four images using the same pose, scale/proportions, and orthographic projection. Reference PNGs are intentionally **not included**. See [input rules](references/README.md).

## Quick start

1. Put the four PNG images into `references/`.
2. Edit `config/reference_setup.json`. Set `character_height_m`, and for **each image** set `head_y`, `foot_y`, `center_x` to the actual normalized pixel positions (0.0–1.0). Defaults assume the character occupies the full PNG height without margins.
3. Check the inputs with Python 3.11+ (no pip packages needed):

   ```bash
   python scripts/check_references.py
   ```

4. Create the prepared Blender scene (Blender 4.x):

   ```bash
   blender --background --factory-startup --python scripts/setup_references.py -- --config config/reference_setup.json --output output/reference_stage.blend
   ```

5. Open `output/reference_stage.blend` in Blender. Check Front/Back/Left/Right Orthographic views and the locked `REF_*` reference images. No base mesh is created yet.

The script does not overwrite an existing .blend by default; add `--overwrite` only if that is intentional. Images are packed into the output .blend; its sibling `reference_stage.manifest.json` records the image calibration and camera IDs. The `output/` folder is ignored by Git.

## Project layout

```text
config/reference_setup.json   # input file names, real-world height and image anchors
references/                  # four user-supplied PNG inputs
scripts/reference_common.py  # input check and scale/translation calibration
scripts/check_references.py  # standalone preflight
scripts/setup_references.py  # Blender scene bootstrap (headless)
docs/workflow.md             # future Builder/Reviewer integration contract
tests/                       # Python-only contract tests
```

## Roadmap

- [x] Four-view input contract, image calibration and validation
- [x] Non-destructive output scene creation with locked reference planes
- [x] Empty Body / Head workspaces and orthographic review cameras
- [ ] Run and inspect integration with local Blender GUI
- [ ] Body / Head builders using these pre-positioned references
- [ ] Automated four-view renders, silhouette comparison, review/rework loop

Run local unit tests with `python -m unittest discover -s tests -v`. Blender runtime execution is not exercised by CI.
