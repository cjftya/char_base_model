# Phase 1 structural follow-up — 2026-11-08

## Implemented

1. **Model/state publication.** Save a new immutable generation alongside the
   working file, hash it, and select it with one atomic state.json replacement.
   Failed model saves and failed state replacement leave the previous committed
   pair usable. An exclusive writer lock prevents simultaneous publication.
   Working/final outputs are derived copies, not the commit point. Failed final
   materialization is recoverable from the committed COMPLETE generation.
2. **Explicit recovery.** recover_working verifies the selected hash, restores
   the working copy and opens it through Blender. Unsaved edits require explicit
   preservation/discard choice. A stale scene generation blocks continued work.
   Lock files left after hard process termination require verifying that no
   writer remains before removal. Orphan generations are never auto-selected.
3. **Staged head specification.** Initial body/shared contract may omit detailed
   head geometry. accept_head is available after body shape approval and binds
   a separate immutable specification without changing approved body inputs.
   Existing full contracts remain valid. Evidence binds the additional hash.
4. **Region identity.** Face region lookup uses vertex membership rather than
   polygon array position. Face reordering and winding changes preserve labels;
   even a same-face-count topology mutation is rejected. Actual new topology
   still requires explicit replanning, not an unsafe automatic label guess.
5. **Reporting.** Reports reject an unrelated or stale scene rather than writing
   its mesh statistics under another session's path.

## Verification

89 automated tests pass (78 prior + 11 new). New tests inject model-save and
state-publication failures, verify successful pair selection, reject corrupt
checkpoints/stale writers/premature final output, recover after final-copy
failure, reject a concurrent publisher, allow deferred head data, preserve
labels after polygon reorder and reject same-count topology changes.
Blender-specific save/reopen behavior, scene generation persistence and actual
model output still need the user's host integration test. Pure filesystem tests
are not presented as Blender tests or as power-loss certification.

## Operational differences and limits

Reopen using recover_working, because phase1_working.blend is a derived snapshot
and is not rewritten for every operation. Generation files are retained for
recovery; no automatic garbage collection deletes old attempts. Older Phase 1
sessions need a new session rather than an inferred migration; Phase 0 data is
compatible. A hard crash can leave a writer lock and orphan generation, both
visible and safely excluded from the selected commit.

The model/state selection is atomic under the local filesystem's replace
semantics; external filesystem durability and power-loss behavior are not
certified. The workflow remains sequential on one Blender host. The head and
body constructors still need measured explicit profiles. Large topology edits,
anatomical correctness, neck fitting, self-intersections and 4K compositing
performance remain separate modeling/host-validation concerns.

Remote publishing has not been retried following the previous approval block.
