# Future modeling role contracts

Phase 0 ends at the review gate in the [Blender MCP workflow](../skills/char-base-model/references/workflow.md). Future modeling depends on `REFERENCES_READY`. The roles below are contracts for later phases.

| Role | Responsibility and write boundary |
| --- | --- |
| Main | Select work, manage phase transitions, and decide approval or targeted rework. Route tasks using the reviewed manifest. |
| Body Builder | Build or refine the body mesh. Write only to `10_BODY_WORKSPACE`. |
| Head Builder | Build or refine cranium and facial geometry. Write only to `20_HEAD_WORKSPACE`. |
| Validator | Read mesh integrity, dimensions, and camera-aligned measurements. Return evidence without editing the scene. |
| Reviewer | Compare the mesh from four directions against the original PNGs. Return `PASS`, `REWORK`, or `REPLAN` with evidence. Scene access is read-only. |

Builders use the locked references and cameras as read-only inputs. Main assigns rework to the affected builder. Four silhouettes leave depth details, concavities, and topology underdetermined.
