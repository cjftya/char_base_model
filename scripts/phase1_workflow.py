"""Pure review state machine; no Blender or filesystem dependency."""
import json
from reference_common import ReferenceError

STATES = ("REFERENCES_READY", "LANDMARKS_READY", "BODY_BLOCKOUT", "BODY_SHAPE_REVIEW",
          "HEAD_BLOCKOUT", "HEAD_SHAPE_REVIEW", "TOPOLOGY_REFINEMENT",
          "INTEGRATION_REVIEW", "PHASE1_COMPLETE")
VISUAL_CHECKS = ("proportions", "silhouette", "volume", "connections", "mesh_validity")

BUILD_START = {"body": "LANDMARKS_READY", "head": "BODY_SHAPE_REVIEW"}
BLOCKOUT = {"body": "BODY_BLOCKOUT", "head": "HEAD_BLOCKOUT"}
REVIEW_NEXT = {"BODY_BLOCKOUT": "BODY_SHAPE_REVIEW", "HEAD_BLOCKOUT": "HEAD_SHAPE_REVIEW",
               "TOPOLOGY_REFINEMENT": "INTEGRATION_REVIEW", "INTEGRATION_REVIEW": "PHASE1_COMPLETE"}

def transition(state, target, *, review=None, evidence=None):
    """Pure transition; caller persists only after Blender operation/evidence save."""
    state = json.loads(json.dumps(state))
    if state["status"] != "ACTIVE":
        raise ReferenceError("Session is halted; start an explicitly replanned session")
    current = state["state"]
    if target not in STATES or STATES.index(target) != STATES.index(current) + 1:
        raise ReferenceError(f"Invalid phase transition: {current} -> {target}")
    if target.endswith("REVIEW") or target == "PHASE1_COMPLETE":
        if not isinstance(review, dict) or not isinstance(evidence, dict):
            raise ReferenceError("An independent review and bound artifacts are required")
        verdict = review.get("verdict")
        if verdict not in ("PASS", "REWORK", "REPLAN", "BLOCKED"):
            raise ReferenceError("Unknown reviewer verdict")
        if not review.get("reviewer") or review.get("role") != "Reviewer":
            raise ReferenceError("Use an independent, read-only Reviewer role")
        if review.get("evidence") != evidence or not evidence:
            raise ReferenceError("Reviewer evidence is missing or stale")
        findings = review.get("findings")
        if not isinstance(findings, list):
            raise ReferenceError("Reviewer findings must be an array")
        keys = {"region", "severity", "evidence", "expected", "observed", "suggested_action", "preserve_regions", "attempt"}
        if any(not isinstance(f, dict) or not keys <= f.keys() for f in findings):
            raise ReferenceError("Incomplete structured finding")
        for finding in findings:
            if (finding["severity"] not in ("info", "warning", "error", "critical")
                    or type(finding["attempt"]) is not int or finding["attempt"] < 1
                    or not isinstance(finding["preserve_regions"], list)
                    or any(not isinstance(r, str) for r in finding["preserve_regions"])
                    or any(not isinstance(finding[k], str) or not finding[k].strip()
                           for k in ("region", "evidence", "expected", "observed", "suggested_action"))):
                raise ReferenceError("Malformed reviewer finding")
        # Topology edits cannot be implemented by the position-only REWORK API.
        for finding in findings:
            change = finding.get("change_type", "position")
            if change not in ("position", "topology"):
                raise ReferenceError("Unknown finding change_type")
        if verdict == "REWORK" and any(f.get("change_type") == "topology" for f in findings):
            verdict = "REPLAN"
        if verdict == "PASS":
            if any(review.get("checks", {}).get(k) != "PASS" for k in VISUAL_CHECKS):
                raise ReferenceError("All visual checks must pass")
            if any(f["severity"] in ("error", "critical") for f in findings):
                raise ReferenceError("PASS cannot contain unresolved errors")
        elif not findings:
            raise ReferenceError("Non-PASS verdict needs actionable findings")
        if verdict == "REWORK":
            count = state["reworks"].get(target, 0) + 1
            state["reworks"][target] = count
            if count > 2:
                verdict = "REPLAN"
        state["history"].append({"gate": target, "verdict": verdict, "review": review})
        if verdict != "PASS":
            if verdict in ("REPLAN", "BLOCKED"):
                state["status"] = verdict
            return state
    state["state"] = target
    if target == "PHASE1_COMPLETE":
        state["status"] = "COMPLETE"
    return state
