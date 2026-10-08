"""
Vidhik Platform - eCourts CNR Validation & Reference Helper
============================================================
Provides deterministic validation and normalization for Indian eCourts
Case Number Record (CNR) identifiers.

Standard 16-Character CNR Format:
  SS DDDD NNNNNN YYYY
  - SS: 2-letter State Code (e.g. MH, DL, KA, UP)
  - DDDD: 4-character District / Court Complex Code (e.g. AU01, HC01)
  - NNNNNN: 6-digit Case Registration / Filing Number (zero-padded)
  - YYYY: 4-digit Filing Year (e.g. 2023)

Example:
  Valid:   MHAU010123452023
  Invalid: MH123, MHAU-010123452023, MHAU 010123452023
"""

import re
from typing import Optional, Tuple, Dict, Any

# Official portal URLs
ECOURTS_SERVICES_PORTAL: str = "https://services.ecourts.gov.in/ecourtindia_v6/"
ECOURTS_MAIN_PORTAL: str = "https://ecourts.gov.in/"

# Regex for standard 16-character alphanumeric CNR: 2 letters (State) + 4 alphanumeric (Court) + 6 digits (Number) + 4 digits (Year)
CNR_REGEX = re.compile(r"^[A-Z]{2}[A-Z0-9]{4}\d{6}\d{4}$")
CNR_GENERAL_16_ALNUM = re.compile(r"^[A-Z0-9]{16}$")


def validate_cnr(cnr: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates and normalizes an Indian eCourts Case Number Record (CNR).

    Rules:
    - Trims leading and trailing whitespace.
    - Converts to uppercase.
    - Must be exactly 16 characters in length.
    - Alphanumeric only (rejects hyphens, slashes, spaces, punctuation).
    - Checks basic structural format (State code prefix + Year suffix).

    Returns:
        (is_valid: bool, normalized_cnr: Optional[str], error_message: Optional[str])
    """
    if cnr is None:
        return False, None, "CNR Number is required."

    raw = str(cnr).strip()
    if not raw:
        return False, None, "CNR Number cannot be empty."

    # Check for forbidden whitespace inside string
    if any(c.isspace() for c in raw):
        return False, None, "CNR Number must not contain spaces. Please enter 16 consecutive characters."

    # Check for hyphens, slashes, punctuation
    if any(not c.isalnum() for c in raw):
        return False, None, "CNR Number must contain alphanumeric characters only (no hyphens, slashes, or symbols)."

    normalized = raw.upper()

    if len(normalized) != 16:
        return (
            False,
            None,
            f"CNR Number must be exactly 16 characters in length (received {len(normalized)} characters)."
        )

    # Validate state code prefix (first 2 chars must be alphabetic letters)
    if not normalized[:2].isalpha():
        return (
            False,
            None,
            "CNR Number must start with a 2-letter state code (e.g. 'MH' for Maharashtra, 'DL' for Delhi)."
        )

    # Validate year suffix (last 4 chars must be valid digits, e.g. 1950 - 2099)
    year_str = normalized[12:16]
    if not year_str.isdigit():
        return (
            False,
            None,
            "CNR Number must end with a 4-digit filing year (e.g. '2023')."
        )

    year_val = int(year_str)
    if year_val < 1900 or year_val > 2100:
        return (
            False,
            None,
            f"Filing year in CNR '{year_val}' is outside the valid judicial range (1900-2100)."
        )

    # Verify overall 16-character alphanumeric pattern
    if not CNR_GENERAL_16_ALNUM.match(normalized):
        return (
            False,
            None,
            "CNR Number format is invalid. Expected 16 alphanumeric characters (e.g. 'MHAU010123452023')."
        )

    return True, normalized, None


def normalize_cnr(cnr: Optional[str]) -> str:
    """
    Normalizes and validates a CNR string.
    Raises ValueError on validation failure.
    """
    is_valid, normalized, err = validate_cnr(cnr)
    if not is_valid or not normalized:
        raise ValueError(err or "Invalid CNR Number format.")
    return normalized


def is_valid_cnr(cnr: Optional[str]) -> bool:
    """
    Returns True if the string is a valid CNR, False otherwise.
    """
    is_valid, _, _ = validate_cnr(cnr)
    return is_valid


def parse_cnr_components(cnr: str) -> Dict[str, Any]:
    """
    Deconstructs a validated 16-character CNR into its informational components.
    """
    is_valid, normalized, err = validate_cnr(cnr)
    if not is_valid or not normalized:
        raise ValueError(err or "Cannot parse invalid CNR.")

    return {
        "cnr_number": normalized,
        "state_code": normalized[0:2],
        "court_complex_code": normalized[2:6],
        "case_filing_number": normalized[6:12],
        "filing_year": int(normalized[12:16]),
        "official_portal_url": ECOURTS_SERVICES_PORTAL
    }


def get_official_ecourts_portal_url() -> str:
    """
    Returns the official eCourts Services portal base URL.
    """
    return ECOURTS_SERVICES_PORTAL
