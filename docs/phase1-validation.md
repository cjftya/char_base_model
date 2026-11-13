# Phase 1 verification status

## Current baseline (2026-11-13)

- Source revision: `041fd0a` (midpoly transitions, junction validation and explicit REPLAN).
- Python unit/regression suite: **119 passed, 0 failed, 0 skipped** in the recorded implementation environment.
- Python compilation and whitespace checks: passed in the recorded implementation environment.
- Blender 4.3.2 background smoke test: passed using **synthetic** Body/Head geometry, including triangle/region accounting and rejection of a collapsed seam.
- GitHub Actions runs `python -m unittest discover -s tests -v` on Python 3.11; the latest baseline workflow succeeded.
- **Real four-reference Blender MCP model retest after the midpoly change: NOT RUN / UNVERIFIED.**

These results are evidence for code-path and synthetic geometry behavior, **not** for anatomical likeness, smooth shoulder/hip flow, absence of global self-intersections or final Phase 1 completion.

## Run the checks

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
blender --background --factory-startup --python-exit-code 2 --python tests/blender_midpoly_smoke.py
```

The Blender command is an optional host-side test; normal unit tests do not require Blender. The GitHub workflow currently runs the unit suite, not the Blender smoke test.

## Actual-character acceptance

Use [Phase 1 modeling](../skills/char-base-model/references/phase1-modeling.md), [independent review rules](../skills/char-base-model/references/phase1-review.md) and [midpoly retest procedure](phase1-midpoly-review.md).

1. Verify the original four image directions, measurements and Phase 0 saved/reopened scene.
2. Create a **new** checkpoint-backed session for a failed topology plan; never re-label a failed model as approved.
3. Inspect real Body render overlays and both obliques for hip/shoulder shelves, folds, calf width and side depth; approve the Body gate only when the evidence supports it.
4. Build and review Head only after Body PASS. Inspect face proportions, neck contact and all six views.
5. Check actual evaluated **Body + Head** triangles against the 30,000 maximum, mesh health, fresh review evidence and committed final state.

Visual likeness and global intersections remain manual checks. The preceding real-model attempt failed Body Shape review and did not produce an accepted Head; the current midpoly revision still requires a separate real-character test.

Historical engineering review/test counts are summarized in [Phase 1 change history](phase1-history.md); full former documents are recoverable in Git history.
