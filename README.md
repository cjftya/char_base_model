# char_base_model

Phase 0 Agent Skill for preparing four orthographic character references in Blender.

## Run through Blender MCP

1. Start Blender and connect your CLI through its existing Blender MCP. The skill checks the scene and available capabilities.
2. Keep this checkout intact and register [skills/char-base-model](skills/char-base-model) using your CLI's project skill mechanism, or ask the CLI to load its `SKILL.md` directly.
3. Give the agent a folder or attach four files named `front`, `back`, `left`, `right`. Each may use `.png`, `.jpg`, or `.jpeg`. Example request — “Use char-base-model with these four images. Save the work under /home/me/models.”
4. The skill copies the inputs into `char_base_YYYYMMDD_HHMMSS` under your specified destination. When omitted, it uses the Blender host's Windows or Linux Downloads directory. Each run contains its references, configuration, Blender copy, and manifest. The skill/harness stays in the checkout.
5. The agent inspects images and calibrates the run-local anchors, then prepares the open Blender scene through MCP. Inputs below 512px on the short side require larger originals. Differing resolutions produce guidance for individual anchor calibration. See the [input rules](skills/char-base-model/references/input-spec.md).
6. Inspect all four views and reopen the saved copy to complete review. Results stay `UNVERIFIED` until the [review checklist](skills/char-base-model/references/workflow.md) passes.

If images are inaccessible to Blender, the agent guides you to save them on its host. Missing views, unsuitable images, or unavailable MCP capabilities produce guidance for the affected input or connection.

## Helpers and optional background Blender

The agent normally invokes these scripts on the Blender host through MCP. For standalone intake, Python 3.11+ uses only the standard library:

```bash
python scripts/prepare_session.py /path/to/input-images
python scripts/prepare_session.py /path/to/input-images --destination /path/to/work-parent
python scripts/prepare_session.py /path/front.jpg /path/back.png /path/left.jpeg /path/right.jpg
```

On Windows, use native paths, quoted when needed. The helper resolves redirected Windows Downloads and Linux XDG Downloads. An explicit destination takes priority and must already exist. The session's initial anchors need actual image inspection before `anchors_reviewed` is set to true.

An optional isolated Blender 4.x background process can use the same prepared session config:

```bash
blender --background --factory-startup --python-exit-code 2 \
  --python scripts/setup_references.py -- \
  --config /path/char_base_YYYYMMDD_HHMMSS/config/reference_setup.json \
  --output /path/char_base_YYYYMMDD_HHMMSS/reference_stage.blend
```

Use a fresh output filename when retrying a save. The background `--overwrite` flag explicitly replaces an earlier output and manifest. The currently open source file is protected.

## Development

```bash
python -m unittest discover -s tests -v
```

Tests cover input headers/calibration, session intake, destination resolution, and scene/output safety with mocked Blender APIs. Actual viewport display, image decoding in Blender, UI locking, and reopen persistence require Blender and real images. See [future role contracts](docs/workflow.md) for later phases.
