"""Low-level format validators. Each returns None on success or an error string."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional

VALID_RACES = {"1002-5", "2028-9", "2054-5", "2076-8", "2106-3", "2131-1", "UNK"}
VALID_ETHNICITIES = {"H", "N", "U", "O"}
VALID_LANGUAGES = {
    "ENG", "SPA", "NAV", "APA", "VIE", "GER", "CHI", "ARA",
    "KOR", "TGL", "JPN", "FRE", "ITA", "RUS", "HIN", "PER",
    "THA", "ZUN", "UND", "NUL",
}
VALID_SEX = {"M", "F", "O", "U", "N"}
VALID_GENDER_IDENTITY = {
    "F", "M", "TF", "TM", "I use a different term", "Don't know", "Prefer not to state",
}
VALID_MARITAL = {"M", "S", "D"}
VALID_LINE_OF_BUSINESS = {
    "medicaid", "chip", "medicare", "medicare/medicaid duals",
    "military insurance (vha/tricare)", "commercial", "uninsured",
    "cash pay", "falling colors", "other payers",
}
VALID_VETERAN_STATUS = {"Active Duty", "Prior Military Service", ""}
VALID_DEPRESSION_SCREENINGS = {
    "PHQ-9", "PHQ-9 (M)", "BDI", "BDI-II", "CES-D", "DEPS", "DADS",
    "GDS", "CSDD", "PRIME MD-PHQ2", "HAMD", "QID-SR", "CAT-DI", "CAD-MDD",
    "PHQ-A", "PHQ-9M",
}
VALID_CONSENT = {"I", "O"}
VALID_AUDIT_OUTCOME = {"Positive", "Negative"}
VALID_YN = {"Y", "N"}
VALID_YNX = {"Y", "N", "X"}
VALID_YNX_U_NA = {"Y", "N", "X", "U", "NA"}
VALID_FOLLOW_UP = {"Y", "N", "X", "M"}
VALID_ADDRESS_TYPE1 = {"H", ""}
VALID_ADDRESS_TYPE2 = {"Temporary housing", "unhoused", "sheltered", ""}
VALID_DEATH_FLAG = {"Y", "N", ""}


def ck_yyyymmdd(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if " " in val:
        return f"Date must not contain spaces, got '{val}'"
    if not re.fullmatch(r"\d{8}", val):
        return f"Expected YYYYMMDD (8 digits), got '{val}'"
    try:
        datetime.strptime(val, "%Y%m%d")
    except ValueError as e:
        return f"Invalid date '{val}': {e}"
    return None


def ck_yyyymmddhhmmss(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if " " in val:
        return f"Datetime must not contain spaces, got '{val}'"
    if not re.fullmatch(r"\d{14}", val):
        return f"Expected YYYYMMDDHHMMSS (14 digits, no spaces), got '{val}'"
    try:
        datetime.strptime(val, "%Y%m%d%H%M%S")
    except ValueError as e:
        return f"Invalid datetime '{val}': {e}"
    return None


def ck_hhmmss(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"\d{6}", val):
        return f"Expected HHMMSS (6 digits), got '{val}'"
    h, m, s = int(val[:2]), int(val[2:4]), int(val[4:])
    if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
        return f"Invalid time '{val}'"
    return None


def ck_zip5(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"\d{5}", val):
        return f"Expected 5-digit zip code, got '{val}'"
    return None


def ck_zip4ext(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"\d{4}", val):
        return f"Expected 4-digit zip extension (no dashes), got '{val}'"
    return None


def ck_npi(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"\d{10}", val):
        return f"Expected 10-digit NPI, got '{val}'"
    return None


def ck_phone_dashes(val: str) -> Optional[str]:
    """XXX-XXX-XXXX format."""
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"\d{3}-\d{3}-\d{4}", val):
        return f"Expected XXX-XXX-XXXX phone format, got '{val}'"
    return None


def ck_phone_nodashes(val: str) -> Optional[str]:
    """10-digit, no dashes."""
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"\d{10}", val):
        return f"Expected 10-digit phone (no dashes), got '{val}'"
    return None


def ck_state2(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"[A-Za-z]{2}", val):
        return f"Expected 2-letter state code, got '{val}'"
    return None


def ck_ssn(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    clean = val.replace("-", "")
    if not re.fullmatch(r"\d{9}", clean):
        return f"Expected SSN as 9 digits or XXX-XX-XXXX, got '{val}'"
    return None


def ck_icd10(val: str) -> Optional[str]:
    """Basic ICD-10 format check: letter followed by digits and optional dot."""
    val = str(val).strip()
    if not val:
        return None
    if not re.fullmatch(r"[A-Za-z]\d{1,2}(\.\w{1,4})?", val):
        return f"Expected ICD-10 code format (e.g., F32.9), got '{val}'"
    return None


def ck_cpt(val: str) -> Optional[str]:
    """CPT/HCPCS code, optionally with modifiers separated by colons."""
    val = str(val).strip()
    if not val:
        return None
    parts = val.split(":")
    code = parts[0].strip()
    if not re.fullmatch(r"[A-Za-z0-9]{4,7}", code):
        return f"Expected CPT/HCPCS code (optionally with :MODIFIER), got '{val}'"
    return None


def ck_in_set(valid_set: set, case_sensitive: bool = True):
    """Factory: returns a checker that validates membership in a set."""
    def checker(val: str) -> Optional[str]:
        v = str(val).strip()
        if not v:
            return None
        check_val = v if case_sensitive else v.lower()
        check_set = valid_set if case_sensitive else {x.lower() for x in valid_set}
        if check_val not in check_set:
            return f"'{v}' not in allowed values: {sorted(valid_set)}"
        return None
    return checker


def ck_no_commas(val: str) -> Optional[str]:
    val = str(val).strip()
    if "," in val:
        return f"Value must not contain commas, got '{val}'"
    return None


def ck_positive_negative(val: str) -> Optional[str]:
    val = str(val).strip()
    if not val:
        return None
    if val not in {"Positive", "Negative"}:
        return f"Expected 'Positive' or 'Negative', got '{val}'"
    return None
