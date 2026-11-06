# char_base_model

Phase 0 Agent Skill for preparing four orthographic character references in Blender.

## Run through Blender MCP

1. Start Blender, open the intended scene, and confirm your CLI agent can query it through its existing Blender MCP connection. The workflow needs scene inspection and Python execution. Viewport inspection is required for final review.
2. Keep the checkout intact. Register the [skill directory](skills/char-base-model) using your CLI's project skill mechanism, or ask the agent to load `skills/char-base-model/SKILL.md` directly from the checkout. Invoke it by name with a request such as “Use char-base-model to prepare Phase 0 in the open Blender scene.”
3. Place `front.png`, `back.png`, `left.png`, and `right.png` under `references/` on the Blender host. Set the character height and each image's anchors in `config/reference_setup.json`. See the [input specification](skills/char-base-model/references/input-spec.md).
4. Follow the [MCP workflow](skills/char-base-model/references/workflow.md). It includes host-side preflight, setup, and four-view review. If the CLI can access the same checkout, run `python scripts/check_references.py` there first for a quick header and anchor check.
5. Inspect the `.blend` copy and its sibling `.manifest.json`. References are packed, and the manifest records the anchors, image dimensions, calibrated size, and scene object names. Treat the result as `UNVERIFIED` until the four-view and reopen checks pass.

## Optional background Blender

Run from the repository root with Blender 4.x. This starts an isolated Blender process and uses the same Phase 0 implementation.

```bash
blender --background --factory-startup --python-exit-code 2 \
  --python scripts/setup_references.py -- \
  --config config/reference_setup.json --output output/reference_stage.blend
```

Use a fresh output path. The optional background `--overwrite` flag replaces an earlier output and its manifest when explicitly requested. The currently open source file is protected. Open the saved copy and use the same visual checklist.

## Development

```bash
python -m unittest discover -s tests -v
```

The standard-library tests cover calibration, input validation, and scene/output safety with mocked Blender APIs. Real viewport display, UI locking, and image persistence need a Blender session and real inputs. See [future role contracts](docs/workflow.md) for later phases.
