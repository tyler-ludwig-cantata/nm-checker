"""Cross-file validation checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import pandas as pd

from nm_checker.validator import Issue, FileResult
from nm_checker.specs import FileSpec


@dataclass
class CrossFileResult:
    issues: List[Issue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")


def _load_df(path: str) -> Optional[pd.DataFrame]:
    from nm_checker.validator import _load_csv
    df, _, err = _load_csv(Path(path))
    if err or df.empty:
        return None
    df = df.fillna("").astype(str).apply(lambda c: c.str.strip())
    return df


def _get_col(df: pd.DataFrame, idx: int) -> pd.Series:
    if idx < len(df.columns):
        return df.iloc[:, idx]
    return pd.Series(dtype=str)


def _norm_id(val: str) -> str:
    """Normalize integer-float strings: '3600.0' -> '3600'."""
    if val.endswith(".0") and val[:-2].isdigit():
        return val[:-2]
    return val


def run_cross_file_checks(
    file_results: Dict[str, FileResult],
) -> CrossFileResult:
    """
    file_results: {file_type -> FileResult}
    Only runs when relevant files are present.
    """
    result = CrossFileResult()

    # Gather loaded DataFrames by type
    dfs: Dict[str, pd.DataFrame] = {}
    for ftype, fr in file_results.items():
        df = _load_df(fr.path)
        if df is not None:
            dfs[ftype] = df

    # ------------------------------------------------------------------
    # 1. ORG ID consistency across all files
    # ------------------------------------------------------------------
    org_ids: Dict[str, str] = {}
    for ftype, df in dfs.items():
        col_a = _get_col(df, 0)
        unique = set(col_a.dropna().unique()) - {""}
        if unique:
            org_ids[ftype] = next(iter(unique))
            if len(unique) > 1:
                result.issues.append(Issue(
                    file=ftype, row=None, col="A", col_name="ORG ID",
                    message=f"Multiple ORG IDs found in {ftype}: {unique}",
                ))

    all_org_id_values = set(org_ids.values())
    if len(all_org_id_values) > 1:
        summary = ", ".join(f"{k}={v}" for k, v in org_ids.items())
        result.issues.append(Issue(
            file="CROSS-FILE", row=None, col="A", col_name="ORG ID",
            message=f"ORG ID is inconsistent across files: {summary}",
        ))

    # ------------------------------------------------------------------
    # 2. MRN consistency: clinical files -> Roster
    # ------------------------------------------------------------------
    CLINICAL_FILE_TYPES = {
        "I-SERV": 1,     # PT MRN column index
        "ALCOHOLUSE": 1,
        "ENCOUNTERS": 1,
        "DEPRESSION": 1,
        "SDOH": 1,
    }
    ROSTER_MRN_IDX = 2  # Roster col C: Local Patient Id

    if "ROSTER" in dfs:
        roster_mrns: Set[str] = set(_get_col(dfs["ROSTER"], ROSTER_MRN_IDX).dropna())
        roster_mrns.discard("")

        for ftype, mrn_idx in CLINICAL_FILE_TYPES.items():
            if ftype not in dfs:
                continue
            df = dfs[ftype]
            for row_idx, row in df.iterrows():
                data_row = int(row_idx) + 2
                if mrn_idx >= len(row):
                    continue
                mrn = str(row.iloc[mrn_idx]).strip()
                if mrn and mrn not in roster_mrns:
                    result.issues.append(Issue(
                        file=ftype, row=data_row, col="B", col_name="PT MRN",
                        message=f"PT MRN '{mrn}' not found in Roster (Local Patient Id)",
                    ))
    else:
        if any(ft in dfs for ft in CLINICAL_FILE_TYPES):
            result.issues.append(Issue(
                file="CROSS-FILE", row=None, col=None, col_name=None,
                message="No Roster file found — cannot validate MRN cross-references",
                severity="WARNING",
            ))

    # ------------------------------------------------------------------
    # 3. Encounter # consistency: ALCOHOLUSE/DEPRESSION/SDOH -> ENCOUNTERS
    # ------------------------------------------------------------------
    ENCOUNTER_LINKED = {
        "ALCOHOLUSE": (1, 2),   # (mrn_idx, enc_idx)
        "DEPRESSION": (1, 2),
        "SDOH": (1, 2),
    }
    ENCOUNTERS_MRN_IDX = 1   # col B
    ENCOUNTERS_ENC_IDX = 19  # col T

    if "ENCOUNTERS" in dfs:
        enc_df = dfs["ENCOUNTERS"]
        # Build set of (mrn, encounter#) tuples
        enc_pairs: Set[tuple] = set()
        for _, row in enc_df.iterrows():
            mrn = _norm_id(str(row.iloc[ENCOUNTERS_MRN_IDX]).strip()) if ENCOUNTERS_MRN_IDX < len(row) else ""
            enc = _norm_id(str(row.iloc[ENCOUNTERS_ENC_IDX]).strip()) if ENCOUNTERS_ENC_IDX < len(row) else ""
            if mrn and enc:
                enc_pairs.add((mrn, enc))
        # Also build just the encounter number set (for looser check)
        enc_nums: Set[str] = {e for _, e in enc_pairs}

        for ftype, (mrn_idx, enc_idx) in ENCOUNTER_LINKED.items():
            if ftype not in dfs:
                continue
            for row_idx, row in dfs[ftype].iterrows():
                data_row = int(row_idx) + 2
                mrn = _norm_id(str(row.iloc[mrn_idx]).strip()) if mrn_idx < len(row) else ""
                enc = _norm_id(str(row.iloc[enc_idx]).strip()) if enc_idx < len(row) else ""
                if enc and enc not in enc_nums:
                    result.issues.append(Issue(
                        file=ftype, row=data_row, col="C", col_name="Encounter #",
                        message=f"Encounter # '{enc}' not found in ENCOUNTERS file",
                    ))
                elif enc and mrn and (mrn, enc) not in enc_pairs:
                    result.issues.append(Issue(
                        file=ftype, row=data_row, col="C", col_name="Encounter #",
                        message=f"Encounter # '{enc}' exists in ENCOUNTERS but not for PT MRN '{mrn}'",
                    ))
    else:
        if any(ft in dfs for ft in ENCOUNTER_LINKED):
            result.issues.append(Issue(
                file="CROSS-FILE", row=None, col=None, col_name=None,
                message="No ENCOUNTERS file found — cannot validate Encounter # cross-references",
                severity="WARNING",
            ))

    # ------------------------------------------------------------------
    # 4. Revocation Roster vs Roster
    # ------------------------------------------------------------------
    if "REVOCATION" in dfs and "ROSTER" in dfs:
        revoc_df = dfs["REVOCATION"]
        # Revocation col B (idx 1) = Local Client ID
        for row_idx, row in revoc_df.iterrows():
            data_row = int(row_idx) + 2
            client_id = str(row.iloc[1]).strip() if len(row) > 1 else ""
            if client_id and client_id not in roster_mrns if "ROSTER" in dfs else True:
                # roster_mrns may not be defined if ROSTER not in dfs
                pass
        if "ROSTER" in dfs:
            roster_mrns_local: Set[str] = set(_get_col(dfs["ROSTER"], ROSTER_MRN_IDX).dropna())
            roster_mrns_local.discard("")
            for row_idx, row in revoc_df.iterrows():
                data_row = int(row_idx) + 2
                client_id = str(row.iloc[1]).strip() if len(row) > 1 else ""
                if client_id and client_id not in roster_mrns_local:
                    result.issues.append(Issue(
                        file="REVOCATION", row=data_row, col="B", col_name="Local Client ID",
                        message=f"Revocation client ID '{client_id}' not found in Roster",
                        severity="WARNING",
                    ))

    return result
