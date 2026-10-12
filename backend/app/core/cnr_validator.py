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
from urllib.parse import urlparse
from typing import Optional, Tuple, Dict, Any

# Official portal URLs
ECOURTS_SERVICES_PORTAL: str = "https://services.ecourts.gov.in/ecourtindia_v6/"
ECOURTS_MAIN_PORTAL: str = "https://ecourts.gov.in/"
OFFICIAL_ECOURTS_PORTAL_URL: str = ECOURTS_SERVICES_PORTAL

# Regex for standard 16-character alphanumeric CNR
CNR_REGEX = re.compile(r"^[A-Z]{2}[A-Z0-9]{4}\d{6}\d{4}$")
CNR_GENERAL_16_ALNUM = re.compile(r"^[A-Z0-9]{16}$")

# Official domain suffixes for authoritative court references
ALLOWED_OFFICIAL_DOMAINS = (
    "ecourts.gov.in",
    "services.ecourts.gov.in",
    "sci.gov.in",
    "judgments.ecourts.gov.in",
    "districts.ecourts.gov.in",
    "gov.in",
    "nic.in",
)


def validate_cnr(cnr: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates and normalizes an Indian eCourts Case Number Record (CNR).

    Rules:
    - Trims leading and trailing whitespace.
    - Strips common formatting delimiters (hyphens, spaces, underscores, slashes).
    - Converts to uppercase.
    - Must be exactly 16 alphanumeric characters in length:
      * Chars 1-2: 2-letter alphabetic State Code (e.g. 'MH', 'DL', 'KA')
      * Chars 3-6: 4-character alphanumeric Court Complex Code (e.g. 'PU01', 'HC01')
      * Chars 7-12: 6-digit numeric Case Registration / Filing Number
      * Chars 13-16: 4-digit numeric Filing Year (1900 - 2100)

    Returns:
        (is_valid: bool, normalized_cnr: Optional[str], error_message: Optional[str])
    """
    if cnr is None:
        return False, None, "CNR Number cannot be empty."

    raw = str(cnr).strip()
    if not raw:
        return False, None, "CNR Number cannot be empty."

    # Normalize delimiters and uppercase
    cleaned = re.sub(r"[\s\-_/]", "", raw).upper()

    if len(cleaned) != 16:
        return (
            False,
            None,
            f"CNR Number must contain exactly 16 characters (received {len(cleaned)})."
        )

    # Validate state code prefix (first 2 chars must be alphabetic letters)
    if not cleaned[:2].isalpha():
        return (
            False,
            None,
            "CNR Number: First 2 characters must be alphabetic state code (e.g. 'MH', 'DL')."
        )

    # Validate court code (chars 3 to 6 must be alphanumeric)
    if not cleaned[2:6].isalnum():
        return (
            False,
            None,
            "CNR Number: Characters 3-6 must be alphanumeric court complex code."
        )

    # Validate case number (chars 7 to 12 must be 6 digits)
    if not cleaned[6:12].isdigit():
        return (
            False,
            None,
            "CNR Number: Characters 7-12 must be a 6-digit numeric case number."
        )

    # Validate year suffix (last 4 chars must be valid digits, e.g. 1900 - 2100)
    year_str = cleaned[12:16]
    if not year_str.isdigit():
        return (
            False,
            None,
            "CNR Number: Last 4 characters must be a 4-digit filing year (e.g. '2024')."
        )

    year_val = int(year_str)
    if year_val < 1900 or year_val > 2100:
        return (
            False,
            None,
            f"CNR Number: Filing year '{year_val}' must be between 1900 and 2100."
        )

    # Verify overall 16-character alphanumeric pattern
    if not CNR_GENERAL_16_ALNUM.match(cleaned):
        return (
            False,
            None,
            "CNR Number format is invalid. Expected 16 alphanumeric characters."
        )

    return True, cleaned, None


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


def validate_official_case_url(url: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates official case URLs to prevent unsafe schemes or non-government domains.
    Returns (is_valid, cleaned_url, error_message).
    """
    if not url:
        return True, None, None

    cleaned = str(url).strip()
    if not cleaned:
        return True, None, None

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() != "https":
        return False, None, "Official court URL must use HTTPS (secure connection required)."

    # Reject URLs with embedded credentials to prevent deceptive URLs.
    if parsed.username is not None or parsed.password is not None:
        return False, None, "Official court URL must not contain embedded credentials."

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        return False, None, "Invalid official case URL structure."

    # Match only official government/court domain names or their subdomains.
    # Localhost and lookalike domains must never be accepted.
    is_allowed = any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in ALLOWED_OFFICIAL_DOMAINS
    )

    if not is_allowed:
        return (
            False,
            None,
            f"Official court URL domain '{hostname}' must belong to an authoritative government court domain (*.gov.in, *.nic.in)."
        )

    return True, cleaned, None


def get_official_ecourts_portal_url() -> str:
    """
    Returns the official eCourts Services portal base URL.
    """
    return ECOURTS_SERVICES_PORTAL


def is_valid_official_case_url(url: Optional[str]) -> bool:
    """
    Returns True if the URL is valid, HTTPS, and belongs to an allowed authoritative court domain.
    """
    if not url or not str(url).strip():
        return False
    is_valid, cleaned, _ = validate_official_case_url(url)
    if not is_valid or not cleaned:
        return False
    parsed = urlparse(cleaned)
    return parsed.scheme.lower() == "https"
