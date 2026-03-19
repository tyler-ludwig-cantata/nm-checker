"""Column specifications for all 7 CCBHC file types."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, List
import re

from nm_checker.formats import (
    ck_yyyymmdd, ck_yyyymmddhhmmss, ck_hhmmss, ck_zip5, ck_zip4ext, ck_npi,
    ck_phone_dashes, ck_phone_nodashes, ck_state2, ck_ssn, ck_icd10, ck_cpt,
    ck_in_set, ck_no_commas, ck_positive_negative,
    VALID_RACES, VALID_ETHNICITIES, VALID_LANGUAGES, VALID_SEX,
    VALID_GENDER_IDENTITY, VALID_MARITAL, VALID_LINE_OF_BUSINESS,
    VALID_VETERAN_STATUS, VALID_DEPRESSION_SCREENINGS, VALID_CONSENT,
    VALID_AUDIT_OUTCOME, VALID_YN, VALID_YNX, VALID_YNX_U_NA,
    VALID_FOLLOW_UP, VALID_DEATH_FLAG,
)

# ---------------------------------------------------------------------------
# Column spec dataclass
# ---------------------------------------------------------------------------
@dataclass
class ColSpec:
    idx: int            # 0-based column index
    letter: str         # Excel-style letter(s)
    name: str           # expected header name (used for matching)
    required: bool      # True = value must not be blank
    checks: List[Callable] = field(default_factory=list)
    notes: str = ""


@dataclass
class FileSpec:
    file_type: str
    filename_pattern: str          # regex (case-insensitive)
    columns: List[ColSpec]
    description: str = ""


# ---------------------------------------------------------------------------
# Helper to build column letter from index (0-based)
# ---------------------------------------------------------------------------
def col_letter(idx: int) -> str:
    """Convert 0-based column index to Excel-style letter(s)."""
    result = ""
    n = idx + 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


# ---------------------------------------------------------------------------
# I-SERV  (7 columns: A-G)
# ---------------------------------------------------------------------------
ISERV_SPEC = FileSpec(
    file_type="I-SERV",
    filename_pattern=r"ccbhc_i-serv_.+_v\d+\.csv",
    description="I-SERV file (initial service / crisis tracking)",
    columns=[
        ColSpec(0, "A", "ORG ID",                              True,  []),
        ColSpec(1, "B", "PT MRN",                              True,  []),
        ColSpec(2, "C", "Date of First Administrative Contact", True,  [ck_yyyymmdd]),
        ColSpec(3, "D", "Date of Initial Evaluation",          True,  [ck_yyyymmdd]),
        ColSpec(4, "E", "Date of First Clinical Visit",        True,  [ck_yyyymmdd]),
        ColSpec(5, "F", "Crisis Episode contact date and time", True,  [ck_yyyymmddhhmmss]),
        ColSpec(6, "G", "Crisis service date and time",        True,  [ck_yyyymmddhhmmss]),
    ],
)

# ---------------------------------------------------------------------------
# ALCOHOL USE  (7 columns: A-G)
# ---------------------------------------------------------------------------
ALCOHOLUSE_SPEC = FileSpec(
    file_type="ALCOHOLUSE",
    filename_pattern=r"ccbhc_alcoholuse_.+_v\d+\.csv",
    description="Alcohol Use screening file",
    columns=[
        ColSpec(0, "A", "ORG ID",         True,  []),
        ColSpec(1, "B", "PT MRN",         True,  []),
        ColSpec(2, "C", "Encounter #",    True,  []),
        ColSpec(3, "D", "Date",           True,  [ck_yyyymmdd]),
        ColSpec(4, "E", "AUDIT or AUDIT C or the single question screening completed. Y or N",
                True,  [ck_in_set(VALID_YN)]),
        ColSpec(5, "F", "Outcome of assessment?",
                True,  [ck_positive_negative]),
        ColSpec(6, "G", "Was brief counseling provided?",
                True,  [ck_in_set(VALID_YN)]),
    ],
)

# ---------------------------------------------------------------------------
# ENCOUNTERS  (96 columns: A-Cr)
# Diagnoses Z-AJ (cols 25-35) = Dx2-Dx12
# CPT codes start at AK (col 36), pairs of (code, description) up to Cr (col 95)
# ---------------------------------------------------------------------------
def _build_encounter_columns() -> List[ColSpec]:
    cols = [
        ColSpec(0,  "A",  "ORG ID",              True,  []),
        ColSpec(1,  "B",  "PT MRN",              True,  []),
        ColSpec(2,  "C",  "PT First Name",        True,  []),
        ColSpec(3,  "D",  "PT Last Name",         True,  []),
        ColSpec(4,  "E",  "PT DOB",              True,  [ck_yyyymmdd]),
        ColSpec(5,  "F",  "PT Sex",              True,  [ck_in_set(VALID_SEX)]),
        ColSpec(6,  "G",  "PT Gender Identity",  False, [ck_in_set(VALID_GENDER_IDENTITY)]),
        ColSpec(7,  "H",  "Race",                True,  [ck_in_set(VALID_RACES)]),
        ColSpec(8,  "I",  "Ethnicity",           True,  [ck_in_set(VALID_ETHNICITIES)]),
        ColSpec(9,  "J",  "Language",            False, [ck_in_set(VALID_LANGUAGES)]),
        ColSpec(10, "K",  "PT Address 1",        False, []),  # blank if unhoused
        ColSpec(11, "L",  "PT Address 2",        False, []),
        ColSpec(12, "M",  "City",                True,  [ck_no_commas]),
        ColSpec(13, "N",  "State",               True,  [ck_state2]),
        ColSpec(14, "O",  "Zip",                 True,  [ck_zip5]),
        ColSpec(15, "P",  "PT Phone",            True,  [ck_phone_dashes]),
        ColSpec(16, "Q",  "PT SSN",              False, [ck_ssn]),
        ColSpec(17, "R",  "Date of Visit",       True,  [ck_yyyymmdd]),
        ColSpec(18, "S",  "Time of Visit",       False, [ck_hhmmss]),
        ColSpec(19, "T",  "Encounter #",         True,  []),
        ColSpec(20, "U",  "Facility Code",       True,  [ck_npi]),
        ColSpec(21, "V",  "Provider of Service First Name",  False, []),
        ColSpec(22, "W",  "Provider of Service Last Name",   False, []),
        ColSpec(23, "X",  "Provider of Service NPI",         False, [ck_npi]),
        ColSpec(24, "Y",  "Primary Diagnosis",   True,  [ck_icd10]),
        # Z-AJ: Dx2-Dx12 (indices 25-35)
    ]
    dx_letters = ["Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ"]
    for i, letter in enumerate(dx_letters, start=1):
        cols.append(ColSpec(24 + i, letter, f"Dx{i + 1}", False, [ck_icd10]))

    # AK = index 36: Procedure Code (required)
    cols.append(ColSpec(36, "AK", "Procedure Code-CPT code", True, [ck_cpt]))
    cols.append(ColSpec(37, "AL", "Procedure Code Description", False, []))

    # CPT codes 2-30: pairs at indices 38-95
    cpt_letters = [
        ("AM", "AN"), ("AO", "AP"), ("AQ", "AR"), ("AS", "AT"),
        ("AU", "AV"), ("AW", "AX"), ("AY", "AZ"), ("BA", "BB"),
        ("BC", "BD"), ("BE", "BF"), ("BG", "BH"), ("BI", "BJ"),
        ("BK", "BL"), ("BM", "BN"), ("BO", "BP"), ("BQ", "BR"),
        ("BS", "BT"), ("BU", "BV"), ("BW", "BX"), ("BY", "BZ"),
        ("CA", "CB"), ("CC", "CD"), ("CE", "CF"), ("CG", "CH"),
        ("CI", "CJ"), ("CK", "CL"), ("CM", "CN"), ("CO", "CP"),
        ("CQ", "CR"),  # spec writes last description col as "Cr"
    ]
    for n, (code_letter, desc_letter) in enumerate(cpt_letters, start=2):
        idx_code = 36 + (n - 1) * 2
        idx_desc = idx_code + 1
        cols.append(ColSpec(idx_code, code_letter, f"CPT Code {n}", False, [ck_cpt]))
        cols.append(ColSpec(idx_desc, desc_letter, f"CPT Code Description {n}", False, []))

    return cols


ENCOUNTERS_SPEC = FileSpec(
    file_type="ENCOUNTERS",
    filename_pattern=r"ccbhc_encounters_.+_v\d+\.csv",
    description="CCBHC Encounter file",
    columns=_build_encounter_columns(),
)

# ---------------------------------------------------------------------------
# DEPRESSION  (9 columns: A-I)
# ---------------------------------------------------------------------------
DEPRESSION_SPEC = FileSpec(
    file_type="DEPRESSION",
    filename_pattern=r"ccbhc_depression_.+_v\d+\.csv",
    description="Depression screening file",
    columns=[
        ColSpec(0, "A", "ORG ID",                    True,  []),
        ColSpec(1, "B", "PT MRN",                    True,  []),
        ColSpec(2, "C", "Encounter #",               True,  []),
        ColSpec(3, "D", "Date of Depression Screening", True, [ck_yyyymmdd]),
        ColSpec(4, "E", "Name of Screening",         True,  [ck_in_set(VALID_DEPRESSION_SCREENINGS, case_sensitive=False)]),
        ColSpec(5, "F", "PHQ9 Total Score (0-27)",   False, []),  # required if G empty
        ColSpec(6, "G", "Other Screening Measure Score", False, []),  # required if F empty
        ColSpec(7, "H", "Outcome of assessment",     True,  [ck_positive_negative]),
        ColSpec(8, "I", "If positive for depression is a follow-up plan in place.",
                True,  [ck_in_set(VALID_FOLLOW_UP)]),
    ],
)

# ---------------------------------------------------------------------------
# SDOH  (9 columns: A-I)
# ---------------------------------------------------------------------------
SDOH_SPEC = FileSpec(
    file_type="SDOH",
    filename_pattern=r"ccbh_sdoh_.+_v\d+\.csv|ccbhc_sdoh_.+_v\d+\.csv",
    description="Social Determinants of Health file",
    columns=[
        ColSpec(0, "A", "ORG ID",             True,  []),
        ColSpec(1, "B", "PT MRN",             True,  []),
        ColSpec(2, "C", "Encounter #",        True,  []),
        ColSpec(3, "D", "Date of Assessment", True,  [ck_yyyymmdd]),
        ColSpec(4, "E", "Housing Insecurity /homeless/inadequate housing",
                False, [ck_in_set(VALID_YNX)]),
        ColSpec(5, "F", "Food Insecurity",    False, [ck_in_set(VALID_YNX)]),
        ColSpec(6, "G", "Utility Insecurity Utilities Concern",
                False, [ck_in_set(VALID_YNX)]),
        ColSpec(7, "H", "Transportation Insecurity",
                False, [ck_in_set(VALID_YNX)]),
        ColSpec(8, "I", "Interpersonal Safety",
                False, [ck_in_set(VALID_YNX_U_NA)]),
    ],
)

# ---------------------------------------------------------------------------
# ROSTER  (69 columns: A-BQ)
# ---------------------------------------------------------------------------
def _build_roster_columns() -> List[ColSpec]:
    cols = [
        ColSpec(0,  "A",  "Sending Facility",        True,  []),
        ColSpec(1,  "B",  "Patient ID Type Code",    True,  []),
        ColSpec(2,  "C",  "Local Patient Id",        True,  []),
        ColSpec(3,  "D",  "First Name",              True,  []),
        ColSpec(4,  "E",  "Middle Name or Initial",  False, [ck_no_commas]),
        ColSpec(5,  "F",  "Last Name",               True,  []),
        ColSpec(6,  "G",  "Date of Birth",           True,  [ck_yyyymmdd]),
        ColSpec(7,  "H",  "Suffix",                  False, [ck_no_commas]),
        ColSpec(8,  "I",  "Title",                   False, [ck_no_commas]),
        ColSpec(9,  "J",  "Death Flag",              False, [ck_in_set(VALID_DEATH_FLAG)]),
        ColSpec(10, "K",  "PT Sex",                  True,  [ck_in_set(VALID_SEX)]),
        ColSpec(11, "L",  "Marital Status",          False, [ck_in_set(VALID_MARITAL)]),
        ColSpec(12, "M",  "SSN",                     False, [ck_ssn]),
        ColSpec(13, "N",  "Race",                    True,  [ck_in_set(VALID_RACES)]),
        ColSpec(14, "O",  "Ethnicity",               True,  [ck_in_set(VALID_ETHNICITIES)]),
        ColSpec(15, "P",  "Religion",                False, [ck_no_commas]),
        ColSpec(16, "Q",  "Language",                False, [ck_in_set(VALID_LANGUAGES)]),
        ColSpec(17, "R",  "Maiden Name",             False, [ck_no_commas]),
        ColSpec(18, "S",  "Veteran Status",          True,  [ck_in_set(VALID_VETERAN_STATUS)]),
        ColSpec(19, "T",  "Date of Death",           False, [ck_yyyymmdd]),
        ColSpec(20, "U",  "Blank",                   False, []),
        ColSpec(21, "V",  "Blank",                   False, []),
        ColSpec(22, "W",  "Former First Name",       False, [ck_no_commas]),
        ColSpec(23, "X",  "Former Last Name",        False, [ck_no_commas]),
        ColSpec(24, "Y",  "Former Middle Name",      False, [ck_no_commas]),
        ColSpec(25, "Z",  "Address Type 1",          True,  []),  # H or blank (if unhoused)
        ColSpec(26, "AA", "Address Line 1",          True,  []),
        ColSpec(27, "AB", "Address Line 2",          False, []),
        ColSpec(28, "AC", "Address Line 3",          False, []),
        ColSpec(29, "AD", "Address Line 4",          False, []),
        ColSpec(30, "AE", "Address City",            True,  [ck_no_commas]),
        ColSpec(31, "AF", "Address State",           True,  [ck_state2]),
        ColSpec(32, "AG", "Address Postal Code",     True,  [ck_zip5]),
        ColSpec(33, "AH", "Address Postal Code Ext", False, [ck_zip4ext]),
        ColSpec(34, "AI", "Address County",          False, [ck_no_commas]),
        ColSpec(35, "AJ", "Address Country",         False, [ck_no_commas]),
        ColSpec(36, "AK", "Address Type 2",          False, []),
        ColSpec(37, "AL", "T2 Address Line 1",       False, [ck_no_commas]),
        ColSpec(38, "AM", "T2 Address Line 2",       False, [ck_no_commas]),
        ColSpec(39, "AN", "T2 Address Line 3",       False, [ck_no_commas]),
        ColSpec(40, "AO", "T2 Address Line 4",       False, [ck_no_commas]),
        ColSpec(41, "AP", "T2 Address City",         False, [ck_no_commas]),
        ColSpec(42, "AQ", "T2 Address State",        False, [ck_state2]),
        ColSpec(43, "AR", "T2 Address Postal Code",  False, [ck_zip5]),
        ColSpec(44, "AS", "T2 Address Postal Code Ext", False, [ck_zip4ext]),
        ColSpec(45, "AT", "T2 Address County",       False, [ck_no_commas]),
        ColSpec(46, "AU", "T2 Address Country",      False, [ck_no_commas]),
        ColSpec(47, "AV", "Home Phone Number",       True,  [ck_phone_nodashes]),
        ColSpec(48, "AW", "Phone Ext",               False, []),
        ColSpec(49, "AX", "Business Phone Number",   False, [ck_phone_nodashes]),
        ColSpec(50, "AY", "Phone Ext",               False, []),
        ColSpec(51, "AZ", "Provider Id",             False, [ck_npi]),
        ColSpec(52, "BA", "Provider Id Type",        False, []),
        ColSpec(53, "BB", "Provider First Name",     False, [ck_no_commas]),
        ColSpec(54, "BC", "Provider Last Name",      False, [ck_no_commas]),
        ColSpec(55, "BD", "Provider Middle Name",    False, [ck_no_commas]),
        ColSpec(56, "BE", "Primary Facility Id",     True,  [ck_npi]),
        ColSpec(57, "BF", "Primary Facility County", True,  []),
        ColSpec(58, "BG", "Emergency Contact First Name",  False, []),
        ColSpec(59, "BH", "Emergency Contact Last Name",   False, []),
        ColSpec(60, "BI", "Emergency Contact Middle Name", False, []),
        ColSpec(61, "BJ", "Emergency Contact Phone Number", False, [ck_phone_nodashes]),
        ColSpec(62, "BK", "Emergency Contact Relationship", False, []),
        ColSpec(63, "BL", "Consent",                False, []),  # required for 42CFR P2 (validated in cross-col)
        ColSpec(64, "BM", "Enrollment Start",        False, [ck_yyyymmdd]),
        ColSpec(65, "BN", "Enrollment End",          False, [ck_yyyymmdd]),
        ColSpec(66, "BO", "Line of Business",        True,  [ck_in_set(VALID_LINE_OF_BUSINESS, case_sensitive=False)]),
        ColSpec(67, "BP", "Consent End Date",        False, [ck_yyyymmdd]),
        ColSpec(68, "BQ", "42 CFR part 2 Patient",  True,  [ck_in_set(VALID_YN)]),
    ]
    return cols


ROSTER_SPEC = FileSpec(
    file_type="ROSTER",
    filename_pattern=r".+_roster_ccbhc_.+_v\d+\.csv",
    description="CCBHC Program Roster file",
    columns=_build_roster_columns(),
)

# ---------------------------------------------------------------------------
# REVOCATION ROSTER  (6 columns: A-F)
# ---------------------------------------------------------------------------
REVOCATION_SPEC = FileSpec(
    file_type="REVOCATION",
    filename_pattern=r".+_revocation_roster_.+_v\d+\.csv",
    description="Revocation Roster file",
    columns=[
        ColSpec(0, "A", "System Code",    True,  []),
        ColSpec(1, "B", "Local Client ID", True, []),
        ColSpec(2, "C", "First Name",      True,  [ck_no_commas]),
        ColSpec(3, "D", "Middle Name",     False, [ck_no_commas]),
        ColSpec(4, "E", "Last Name",       True,  [ck_no_commas]),
        ColSpec(5, "F", "Date of Birth",   True,  [ck_yyyymmdd]),
    ],
)

ALL_SPECS = [
    ISERV_SPEC,
    ALCOHOLUSE_SPEC,
    ENCOUNTERS_SPEC,
    DEPRESSION_SPEC,
    SDOH_SPEC,
    ROSTER_SPEC,
    REVOCATION_SPEC,
]


def detect_file_type(filename: str) -> Optional[FileSpec]:
    """Match a CSV filename to a file spec using filename patterns."""
    name_lower = filename.lower()
    for spec in ALL_SPECS:
        if re.search(spec.filename_pattern, name_lower):
            return spec
    return None
