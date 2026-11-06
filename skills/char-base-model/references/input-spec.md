# Reference inputs

| Default PNG | View | Camera location | Plane |
| --- | --- | --- | --- |
| `references/front.png` | Front | −Y | XZ |
| `references/back.png` | Back | +Y | XZ |
| `references/left.png` | Left | −X | YZ |
| `references/right.png` | Right | +X | YZ |

View names follow Blender's viewport convention. Use four distinct PNGs of the same character, proportions, and pose. An A-pose with minimal occlusion and orthographic projection is preferred. Blender must be able to read the files on its own host. The paths in `config/reference_setup.json` are relative to the checkout root, including after resolving symlinks.

Each image needs normalized anchors measured from the top left of the canvas. Set `head_y` at the crown, `foot_y` at the sole, and `center_x` at the body centerline. Values are between 0 and 1 with `head_y < foot_y`. Defaults describe an image with no top or bottom margin. Confirm actual anchors before running.

Calibration uses one uniform scale per image and retains the PNG's aspect ratio. The crown is placed at Z = `character_height_m`, soles at Z = 0, and centerlines at X = 0 in front/back and Y = 0 in left/right. The numbers are Blender world units, with one unit per meter in the project convention. The active scene's unit display settings are preserved. The `plane_offset_m` setting places each plane on its camera's side. Pose mismatch, perspective, mislabeled views, and mirrors require manual review.
