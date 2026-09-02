"""Case and chain-of-custody management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from secintel_core.security import bounded_read_file


@dataclass(frozen=True)
class CustodyEvent:
    item_id: str
    from_party: str
    to_party: str
    at: str
    action: str


@dataclass(frozen=True)
class EvidenceItem:
    item_id: str
    description: str
    hash_sha256: str
    received_at: str
    custodian: str


@dataclass
class CaseRecord:
    case_id: str
    title: str
    opened_at: str
    investigator: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    custody: list[CustodyEvent] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def load_case(path: Path) -> CaseRecord:
    data = json.loads(bounded_read_file(path, max_bytes=5 * 1024 * 1024))
    evidence = [
        EvidenceItem(
            item_id=e["item_id"],
            description=e.get("description", ""),
            hash_sha256=e.get("hash_sha256", ""),
            received_at=e.get("received_at", ""),
            custodian=e.get("custodian", ""),
        )
        for e in data.get("evidence", [])
    ]
    custody = [
        CustodyEvent(
            item_id=c["item_id"],
            from_party=c.get("from", ""),
            to_party=c.get("to", ""),
            at=c.get("at", ""),
            action=c.get("action", ""),
        )
        for c in data.get("chain_of_custody", [])
    ]
    case = CaseRecord(
        case_id=str(data.get("case_id", "")),
        title=str(data.get("title", "")),
        opened_at=str(data.get("opened_at", "")),
        investigator=str(data.get("investigator", "")),
        evidence=evidence,
        custody=custody,
    )
    # Integrity checks
    evidence_ids = {e.item_id for e in evidence}
    for event in custody:
        if event.item_id not in evidence_ids:
            case.issues.append(f"Custody references unknown item {event.item_id}")
    for e in evidence:
        if len(e.hash_sha256) != 64:
            case.issues.append(f"Evidence {e.item_id} missing valid SHA-256")
        if not any(c.item_id == e.item_id for c in custody):
            case.issues.append(f"Evidence {e.item_id} has no custody events")
    return case
