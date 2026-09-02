"""Tests."""

from pathlib import Path

from forensic_case_manager.core import analyze_case

FIXTURES = Path(__file__).resolve().parent.parent / "sample_data"


class TestForensicCaseManager:
    def test_loads_case(self) -> None:
        r = analyze_case(FIXTURES / "sample_case.json")
        assert r.case.case_id == "CASE-2026-001"

    def test_evidence_count(self) -> None:
        r = analyze_case(FIXTURES / "sample_case.json")
        assert len(r.case.evidence) == 2

    def test_flags_missing_custody(self) -> None:
        r = analyze_case(FIXTURES / "sample_case.json")
        assert any("E-002" in i for i in r.case.issues)
