"""Core forensic case management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from secintel_core import (
    Classification,
    Confidence,
    Evidence,
    Finding,
    InputArtifact,
    Provenance,
    Report,
    Severity,
    build_environment_info,
    canonical_config_hash,
    deterministic_finding_id,
    reproducible_now,
    sha256_file,
)
from secintel_core.security import safe_resolve_path

from forensic_case_manager.case import CaseRecord, load_case

TOOL_NAME = "forensic-case-manager"
TOOL_VERSION = "0.1.0"


@dataclass
class AnalysisConfig:
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    max_bytes: int = 50 * 1024 * 1024


@dataclass
class AnalysisResult:
    report: Report
    case: CaseRecord


def _resolve(base: Path, p: Path | str) -> Path:
    up = Path(p)
    return up.resolve() if up.is_absolute() else safe_resolve_path(base, p)


def analyze_case(
    input_path: Path | str,
    *,
    config: AnalysisConfig | None = None,
    is_sample: bool = False,
) -> AnalysisResult:
    cfg = config or AnalysisConfig()
    resolved = _resolve(cfg.base_dir, input_path)
    if not resolved.is_file():
        raise ValueError(f"Case file not found: {resolved}")
    input_hash = sha256_file(resolved, max_bytes=cfg.max_bytes)
    started = reproducible_now()
    case = load_case(resolved)
    findings: list[Finding] = [
        Finding(
            id=deterministic_finding_id("case-observed", input_hash, {"id": case.case_id}),
            title=f"Case {case.case_id}: {case.title}",
            classification=Classification.OBSERVED,
            evidence=[Evidence(source=str(resolved), locator={"evidence": len(case.evidence), "custody": len(case.custody)}, retrieved_at=started)],
            method="Case intake JSON parsing",
            why_it_matters="Chain-of-custody starts with documented intake.",
            plain_language=f"Loaded case with {len(case.evidence)} evidence item(s).",
            severity=Severity.INFO,
            tags=["case"],
            timestamp=started,
        )
    ]
    for issue in case.issues:
        findings.append(
            Finding(
                id=deterministic_finding_id("custody-issue", input_hash, {"issue": issue}),
                title=f"Custody issue: {issue}",
                classification=Classification.INFERRED,
                confidence=Confidence(score=0.90, rationale=issue, supporting_indicators=[case.case_id]),
                evidence=[Evidence(source=str(resolved), locator={"issue": issue}, retrieved_at=started)],
                method="Chain-of-custody integrity checks",
                why_it_matters="Broken custody weakens evidentiary value.",
                plain_language=issue,
                severity=Severity.HIGH,
                tags=["custody", "integrity"],
                timestamp=started,
            )
        )
    ended = reproducible_now()
    report = Report(
        provenance=Provenance(
            tool_name=TOOL_NAME,
            tool_version=TOOL_VERSION,
            config_hash=canonical_config_hash({}),
            inputs=[InputArtifact(path=str(resolved), sha256=input_hash, size_bytes=resolved.stat().st_size)],
            analysis_started_at=started,
            analysis_ended_at=ended,
            environment=build_environment_info(),
        ),
        findings=findings,
        is_sample_data=is_sample,
        metadata={"case_id": case.case_id, "evidence_count": len(case.evidence), "issue_count": len(case.issues)},
    )
    return AnalysisResult(report=report, case=case)
