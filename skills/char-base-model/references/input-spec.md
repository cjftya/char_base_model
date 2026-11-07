# Reference inputs

Accept an image folder or four attached images with these base filenames.

| Basename | View | Camera location | Plane |
| --- | --- | --- | --- |
| `front` | Front | −Y | XZ |
| `back` | Back | +Y | XZ |
| `left` | Left | −X | YZ |
| `right` | Right | +X | YZ |

Each extension may be `.png`, `.jpg`, or `.jpeg`, including a mixture of formats. Names and extensions are case-insensitive during intake and normalized in the session. Keep exactly one file per direction. Additional unrelated files in a supplied folder are ignored.

Use four images of the same character, proportions, and pose. View names follow Blender's viewport convention. Prefer an A-pose and orthographic projection. Compare the actual images with the labels, including asymmetrical landmarks and upright orientation. Export JPEGs upright if a viewer rotates them through EXIF metadata. Re-export corrupted or unreadable images from their original source.

Session intake requires a short side of at least 512px. Prefer 1024px or more and a character large enough in the canvas for visible body and face boundaries. This is a project intake threshold. The script checks dimensions from headers and Blender performs full decoding. Header validation alone cannot attest to image quality.

Different image resolutions generate guidance, including each image's dimensions. Prefer matching canvas size and character proportions. Different padding or canvas dimensions can be calibrated separately if the source character is consistent. Pose, perspective, cropping through crown/soles, and mirrored/mislabeled views require correction before setup. Do not stretch images independently to hide inconsistencies.

The agent measures normalized anchors from the top left of each image. Set `head_y` at the crown, `foot_y` at the sole, and `center_x` at the body centerline in the generated session config. Values are between 0 and 1 with `head_y < foot_y`. The initial 0/1/0.5 values are placeholders. Set `anchors_reviewed=true` after actual image inspection and calibration. Preserve this review gate if setup is retried.

The default character height is 1.6 world units, one unit per meter in the project convention. Use the user's requested height when provided. Uniform scale preserves aspect ratio, maps crown to the selected height and soles to Z=0, and centers the body at X=0 or Y=0. The source scene's unit display settings are preserved.
