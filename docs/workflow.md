# Modeling pipeline (planned boundaries)

This repository currently implements **Phase 0: reference stage setup**, not mesh creation.

1. **Preflight**: require four consistent orthographic PNGs, confirm they decode, calibrate crown/sole/centerline.
2. **Scene bootstrap (implemented)**: set units, lock viewport references, create BODY/HEAD workspace collections, add four review cameras, save portable .blend + JSON manifest. Missing references cause a hard failure.
3. **Body Builder (future)**: create and adjust 3D body geometry against front, back and side reference constraints. Work only in `10_BODY_WORKSPACE`.
4. **Head Builder (future)**: build cranium and facial geometry, not a placeholder sphere. Work only in `20_HEAD_WORKSPACE`.
5. **Automatic Validator (future)**: inspect mesh dimensions, object integrity, non-manifold issues, camera-aligned silhouette metrics. Separate reference Empties from rendered evaluation.
6. **Reviewer (future)**: compare renders and original references, return PASS, REWORK or REPLAN with concrete evidence. Reviewer does not edit the mesh.
7. **Main agent (future)**: assign the relevant part builder; do not redo approved parts when only one part fails.

## Coordinate / camera contract

- Blender world: Z is up, feet are at Z=0, crown at Z=`character_height_m`.
- `front` is viewed from -Y; `back` from +Y; `left` from -X; `right` from +X.
- Front/back images occupy XZ planes, left/right occupy YZ planes.
- Four reference Empty images are view-only and packed into the scene; they are not included in image renders.
- Cameras `CAM_FRONT/BACK/LEFT/RIGHT` are orthographic and fixed.
- Lock inputs before builders are permitted to run. Builders must not edit or move reference objects.

## Important limitations

- Matching four silhouettes cannot uniquely determine concave surfaces, face detail, joints, or topology.
- Input reference images must already be consistent. Calibration corrects scale/translation only, not pose/perspective deformation.
- Blender runtime integration is not covered by the Python-only CI tests. Open the generated .blend and visually inspect plane orientation before enabling any automated modeling agents.
