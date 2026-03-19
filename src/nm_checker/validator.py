"""Per-file validation engine."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import pandas as pd

from nm_checker.specs import FileSpec, ColSpec


@dataclass
class Issue:
    file: str
    row: Optional[int]   # 1-based data row (None = file-level)
    col: Optional[str]   # column letter
    col_name: Optional[str]
    message: str
    severity: str = "ERROR"  # ERROR or WARNING

    def __str__(self) -> str:
        loc = f"row {self.row}" if self.row else "file"
        col = f" col {self.col} ({self.col_name})" if self.col else ""
        return f"[{self.severity}] {self.file}{col} [{loc}]: {self.message}"


@dataclass
class FileResult:
    path: str
    file_type: Optional[str]
    issues: List[Issue] = field(default_factory=list)
    row_count: int = 0
    detected: bool = True

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")

    @property
    def passed(self) -> bool:
        return self.error_count == 0


def _detect_delimiter(path: Path) -> str:
    """Auto-detect comma vs pipe delimiter by sampling first line."""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        first = f.readline()
    pipes = first.count("|")
    commas = first.count(",")
    return "|" if pipes > commas else ","


def _load_csv(path: Path) -> tuple[pd.DataFrame, str, Optional[str]]:
    """Load CSV, auto-detecting delimiter. Returns (df, delimiter, error_msg)."""
    delim = _detect_delimiter(path)
    try:
        df = pd.read_csv(
            path,
            sep=delim,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
        )
        return df, delim, None
    except Exception as e:
        return pd.DataFrame(), delim, str(e)


def validate_file(path: Path, spec: FileSpec) -> FileResult:
    result = FileResult(path=str(path), file_type=spec.file_type)

    df, delim, load_err = _load_csv(path)
    if load_err:
        result.issues.append(Issue(
            file=path.name, row=None, col=None, col_name=None,
            message=f"Failed to load file: {load_err}",
        ))
        result.detected = False
        return result

    result.row_count = len(df)
    fname = path.name

    # --- Column count check ------------------------------------------------
    expected_min = len(spec.columns)
    actual = len(df.columns)
    if actual < expected_min:
        result.issues.append(Issue(
            file=fname, row=None, col=None, col_name=None,
            message=f"Expected at least {expected_min} columns, found {actual}",
        ))

    # --- Header name check (positional) ------------------------------------
    for cs in spec.columns:
        if cs.idx >= len(df.columns):
            result.issues.append(Issue(
                file=fname, row=None, col=cs.letter, col_name=cs.name,
                message=f"Column {cs.letter} ({cs.name}) is missing",
            ))
        else:
            actual_hdr = str(df.columns[cs.idx]).strip()
            if actual_hdr.lower() != cs.name.lower():
                result.issues.append(Issue(
                    file=fname, row=None, col=cs.letter, col_name=cs.name,
                    message=f"Column {cs.letter}: expected header '{cs.name}', found '{actual_hdr}'",
                    severity="WARNING",
                ))

    # --- Row-level validation ----------------------------------------------
    for row_idx, row in df.iterrows():
        data_row = int(row_idx) + 2  # +1 for header, +1 for 1-based
        row_vals = list(row)

        for cs in spec.columns:
            if cs.idx >= len(row_vals):
                continue
            val = str(row_vals[cs.idx]).strip()

            # Required check
            if cs.required and not val:
                result.issues.append(Issue(
                    file=fname, row=data_row, col=cs.letter, col_name=cs.name,
                    message=f"Required field is empty",
                ))
                continue  # skip format checks if empty

            # Format checks
            for check_fn in cs.checks:
                err = check_fn(val)
                if err:
                    result.issues.append(Issue(
                        file=fname, row=data_row, col=cs.letter, col_name=cs.name,
                        message=err,
                    ))

        # --- Cross-column checks per file type ----------------------------
        if spec.file_type == "DEPRESSION":
            _check_depression_row(fname, data_row, row_vals, result)

        if spec.file_type == "ROSTER":
            _check_roster_row(fname, data_row, row_vals, result)

    return result


def _check_depression_row(fname: str, data_row: int, vals: list, result: FileResult):
    """Enforce that either PHQ9 score (col F, idx 5) or Other score (col G, idx 6) is filled."""
    if len(vals) < 7:
        return
    phq9 = str(vals[5]).strip()
    other = str(vals[6]).strip()
    if not phq9 and not other:
        result.issues.append(Issue(
            file=fname, row=data_row, col="F/G", col_name="PHQ9 or Other Score",
            message="At least one of PHQ9 Total Score (F) or Other Screening Score (G) must be filled",
        ))
    if phq9:
        try:
            score = int(phq9)
            if not (0 <= score <= 27):
                result.issues.append(Issue(
                    file=fname, row=data_row, col="F", col_name="PHQ9 Total Score",
                    message=f"PHQ9 score must be 0-27, got '{phq9}'",
                ))
        except ValueError:
            result.issues.append(Issue(
                file=fname, row=data_row, col="F", col_name="PHQ9 Total Score",
                message=f"PHQ9 score must be an integer, got '{phq9}'",
            ))


def _check_roster_row(fname: str, data_row: int, vals: list, result: FileResult):
    """42CFR P2 consent consistency check."""
    if len(vals) < 69:
        return
    cfr_patient = str(vals[68]).strip().upper()  # BQ
    consent = str(vals[63]).strip()              # BL
    if cfr_patient == "Y":
        if consent not in {"I", "O"}:
            result.issues.append(Issue(
                file=fname, row=data_row, col="BL", col_name="Consent",
                message=f"42CFR P2 patient (BQ=Y) must have Consent (BL) = 'I' or 'O', got '{consent}'",
            ))
    elif cfr_patient == "N":
        if consent:
            result.issues.append(Issue(
                file=fname, row=data_row, col="BL", col_name="Consent",
                message=f"Non-42CFR P2 patient (BQ=N) should have blank Consent (BL), got '{consent}'",
                severity="WARNING",
            ))
    # Death consistency: if Death Flag (J, idx 9) = Y, Date of Death (T, idx 19) should be set
    death_flag = str(vals[9]).strip().upper() if len(vals) > 9 else ""
    date_of_death = str(vals[19]).strip() if len(vals) > 19 else ""
    if death_flag == "Y" and not date_of_death:
        result.issues.append(Issue(
            file=fname, row=data_row, col="T", col_name="Date of Death",
            message="Death Flag (J) = Y but Date of Death (T) is empty",
            severity="WARNING",
        ))
