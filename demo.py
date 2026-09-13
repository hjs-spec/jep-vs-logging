#!/usr/bin/env python3
"""Small JEP-vs-logging demonstration.

The script compares text logs with unsigned local hash envelopes. It does not
implement Core 0.6 signatures, HJS receipts, JAC declarations or authenticity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

OUT_DIR = Path("out")
AUDIT_LOG_PATH = OUT_DIR / "audit.log"
JEP_ARCHIVE_PATH = OUT_DIR / "jep_archive.json"


def canonical_json(value: dict[str, Any]) -> str:
    """Serialize an event deterministically for portable hashing."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def compute_event_hash(event: dict[str, Any]) -> str:
    """Compute the hash over canonical event semantics, excluding event_hash."""
    material = deepcopy(event)
    material.pop("event_hash", None)
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def build_event(
    *,
    actor: str,
    intent: str,
    delegation: dict[str, str],
    authority_scope: list[str],
    previous_event_hash: str | None,
) -> dict[str, Any]:
    """Build a canonicalized, hash-linked JEP event."""
    event: dict[str, Any] = {
        "actor": actor,
        "intent": intent,
        "delegation": delegation,
        "authority_scope": authority_scope,
        "previous_event_hash": previous_event_hash,
        "verification_state": "pending",
    }
    event["event_hash"] = compute_event_hash(event)
    event["verification_state"] = "verified"
    event["event_hash"] = compute_event_hash(event)
    return event


def generate_audit_log() -> list[str]:
    """Generate ordinary audit log lines."""
    return [
        "agent called tool",
        "tool returned repository status",
        "agent produced answer",
    ]


def generate_jep_archive() -> list[dict[str, Any]]:
    """Generate a replay-verifiable JEP event archive."""
    first = build_event(
        actor="agent.alice",
        intent="answer user request by checking repository state",
        delegation={
            "from": "user",
            "to": "agent.alice",
            "reason": "inspect repository and produce explanation",
        },
        authority_scope=["read_repo", "run_demo"],
        previous_event_hash=None,
    )
    second = build_event(
        actor="tool.shell",
        intent="read repository status for delegated agent task",
        delegation={
            "from": "agent.alice",
            "to": "tool.shell",
            "reason": "collect evidence needed for the user request",
        },
        authority_scope=["read_repo"],
        previous_event_hash=first["event_hash"],
    )
    third = build_event(
        actor="agent.alice",
        intent="explain the accountability result to the user",
        delegation={
            "from": "tool.shell",
            "to": "agent.alice",
            "reason": "return verified evidence for final response",
        },
        authority_scope=["read_repo", "write_answer"],
        previous_event_hash=second["event_hash"],
    )
    return [first, second, third]


def write_outputs() -> None:
    """Write both demo artifacts."""
    OUT_DIR.mkdir(exist_ok=True)
    AUDIT_LOG_PATH.write_text("\n".join(generate_audit_log()) + "\n", encoding="utf-8")
    JEP_ARCHIVE_PATH.write_text(
        json.dumps(generate_jep_archive(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def replay_verify_jep_archive(events: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Replay and verify required semantics, canonical hashes, and chain links."""
    errors: list[str] = []
    previous_hash: str | None = None
    required_fields = {
        "actor",
        "intent",
        "delegation",
        "authority_scope",
        "event_hash",
        "previous_event_hash",
        "verification_state",
    }

    for index, event in enumerate(events):
        missing = sorted(required_fields.difference(event))
        if missing:
            errors.append(f"event {index}: missing required fields: {', '.join(missing)}")
            continue

        if event["previous_event_hash"] != previous_hash:
            errors.append(
                f"event {index}: previous_event_hash mismatch "
                f"(expected {previous_hash!r}, got {event['previous_event_hash']!r})"
            )

        actual_hash = compute_event_hash(event)
        if event["event_hash"] != actual_hash:
            errors.append(
                f"event {index}: event_hash mismatch "
                f"(expected {actual_hash}, got {event['event_hash']})"
            )

        if event["verification_state"] != "verified":
            errors.append(f"event {index}: verification_state is not verified")

        if not isinstance(event["delegation"], dict) or not {"from", "to", "reason"}.issubset(
            event["delegation"]
        ):
            errors.append(f"event {index}: delegation lineage is incomplete")

        if not isinstance(event["authority_scope"], list) or not event["authority_scope"]:
            errors.append(f"event {index}: authority_scope is empty or invalid")

        previous_hash = event.get("event_hash")

    return not errors, errors


def ordinary_log_replay_status(lines: list[str]) -> tuple[bool, str]:
    """Explain why ordinary log lines cannot replay verify JEP semantics."""
    required_semantics = [
        "actor",
        "intent",
        "delegation",
        "authority_scope",
        "event_hash",
        "previous_event_hash",
        "verification_state",
    ]
    if lines and all(isinstance(line, str) for line in lines):
        return (
            False,
            "missing " + ", ".join(required_semantics[:-1]) + f", and {required_semantics[-1]}",
        )
    return False, "no replayable events found"


def load_archive(path: Path) -> list[dict[str, Any]]:
    """Load a JEP archive from disk."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError("archive must be a JSON list of events")
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and verify JEP-vs-logging demo artifacts.")
    parser.add_argument("--verify", type=Path, help="verify an existing JEP archive instead of generating one")
    args = parser.parse_args()

    if args.verify:
        ok, errors = replay_verify_jep_archive(load_archive(args.verify))
        if ok:
            print(f"Local hash consistency passed (unsigned demo): {args.verify}")
            return 0
        print(f"Local hash consistency failed: {args.verify}")
        for error in errors:
            print(f"- {error}")
        return 1

    write_outputs()
    log_lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    ordinary_ok, ordinary_reason = ordinary_log_replay_status(log_lines)
    jep_ok, jep_errors = replay_verify_jep_archive(load_archive(JEP_ARCHIVE_PATH))

    print(f"Wrote ordinary audit log: {AUDIT_LOG_PATH}")
    print(f"Wrote local demo envelope archive: {JEP_ARCHIVE_PATH}")
    print("\nReplay check:")
    if ordinary_ok:
        print("- ordinary audit log: replay verification passed")
    else:
        print(
            "- ordinary audit log: cannot replay verify accountability semantics "
            f"({ordinary_reason})"
        )

    if jep_ok:
        print("- local envelope: hash consistency passed; no Core signature verification")
        return 0

    print("- local envelope: hash consistency failed")
    for error in jep_errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
