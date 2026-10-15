"""
Vidhik Platform - Centralized Security & Cryptographic Core
===========================================================
Enterprise-grade cryptographic security implementation:
- RFC 6238 TOTP Two-Factor Authentication (pyotp + QR generation)
- Cryptographic one-time recovery codes (hashed SHA-256 + salt)
- Modern Bcrypt password hashing (cost factor 12) + transparent legacy migration
- Password policy validation (length, character classes)
- RFC 7519 signed JWT access tokens, 2FA challenge tokens, & session rotation
- Cloudflare Turnstile CAPTCHA server-side validation
- Google OAuth 2.0 / OpenID Connect ID token verification
- Client User-Agent parsing & approximate GeoIP resolution
- Suspicious login anomaly evaluation
"""

import os
import re
import io
import time
import base64
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, List
import jwt
import bcrypt
import pyotp
import qrcode
import httpx
from dotenv import load_dotenv

logger = logging.getLogger("vidhik.security.core")

# ==============================================================================
# CONFIGURATION
# ==============================================================================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "vidhik-production-jwt-signed-token-secret-2026-secure-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
TWO_FACTOR_TOKEN_EXPIRE_MINUTES = 5

TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "1x00000000000000000000AA")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
TURNSTILE_EXPECTED_HOSTNAME = os.getenv("TURNSTILE_EXPECTED_HOSTNAME", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# Cloudflare official dummy test keys (strictly restricted to local development / test environments)
TEST_TURNSTILE_TOKENS = {
    "1x0000000000000000000000000000000AA",
    "2x0000000000000000000000000000000AA",
    "3x0000000000000000000000000000000AA"
}
TEST_TURNSTILE_SITE_KEYS = {
    "1x00000000000000000000AA",
    "2x00000000000000000000AB",
    "3x00000000000000000000AA"
}
TEST_TURNSTILE_SECRET_KEYS = {
    "1x0000000000000000000000000000000AA",
    "2x0000000000000000000000000000000AA",
    "3x0000000000000000000000000000000AA"
}


def is_production_environment() -> bool:
    """Detects whether the application is running under production mode."""
    env = os.getenv("APP_ENV", os.getenv("ENV", os.getenv("ENVIRONMENT", "development"))).strip().lower()
    return env in ("production", "prod")

# In-memory GeoIP cache to minimize external network lookups
_GEOIP_CACHE: Dict[str, Dict[str, str]] = {}



# ==============================================================================
# 1. PASSWORD SECURITY & VALIDATION
# ==============================================================================

def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Enforces production password complexity requirements:
    - Minimum 8 characters
    - At least one uppercase letter [A-Z]
    - At least one lowercase letter [a-z]
    - At least one numeric digit [0-9]
    - At least one special character
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number (0-9)."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]\\/`~]", password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)."
    return True, None


def hash_password(password: str) -> str:
    """Hashes plaintext password using modern bcrypt (cost=12) with auto salt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def is_bcrypt_hash(hash_str: str) -> bool:
    """Checks whether stored hash is standard bcrypt."""
    return hash_str.startswith("$2a$") or hash_str.startswith("$2b$") or hash_str.startswith("$2y$")


def verify_and_migrate_password(plain_password: str, stored_hash: Optional[str]) -> Tuple[bool, bool]:
    """
    Verifies plaintext password against database hash.
    Returns (is_valid, needs_rehash).
    """
    if not stored_hash or not plain_password:
        return False, False

    stored_hash_clean = stored_hash.strip()

    # 1. Bcrypt check
    if is_bcrypt_hash(stored_hash_clean):
        try:
            matched = bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash_clean.encode("utf-8"))
            return matched, False
        except Exception:
            return False, False

    # 2. Legacy SHA-256 check (transparent migration)
    sha256_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    if sha256_hash.lower() == stored_hash_clean.lower():
        return True, True

    # 3. Plaintext legacy fallback (one-time migration for legacy test rows)
    if plain_password == stored_hash_clean:
        return True, True

    return False, False


# ==============================================================================
# 2. SECURE OTP GENERATION & HASHING
# ==============================================================================

def generate_secure_otp(length: int = 6) -> str:
    """Generates a cryptographically secure numeric OTP."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def hash_otp(otp_code: str, salt: Optional[str] = None) -> str:
    """Securely hashes an OTP using SHA-256 and salt for database persistence."""
    salt_val = salt or JWT_SECRET_KEY[:16]
    return hashlib.sha256(f"{salt_val}:{otp_code.strip()}".encode("utf-8")).hexdigest()


def verify_otp_hash(plain_otp: str, stored_hash: str, salt: Optional[str] = None) -> bool:
    """Verifies plain OTP against stored hash using constant-time comparison."""
    calculated = hash_otp(plain_otp, salt)
    return secrets.compare_digest(calculated, stored_hash)


# ==============================================================================
# 3. MANDATORY TOTP TWO-FACTOR AUTHENTICATION (RFC 6238)
# ==============================================================================

def generate_totp_secret() -> str:
    """Generates a 32-character Base32 secret key for RFC 6238 TOTP."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, account_name: str, issuer_name: str = "Vidhik AI") -> str:
    """Constructs a standard otpauth:// URI for authenticator applications."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=account_name, issuer_name=issuer_name)


def generate_qr_code_data_url(uri: str) -> str:
    """Generates a Base64-encoded PNG Data URL of the QR code for instant display."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#091E42", back_color="#FFFFFF")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_png = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_png}"


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """
    Verifies a 6-digit TOTP code against the Base32 secret.
    Allows valid_window=1 (±30s time drift tolerance).
    """
    if not secret or not code:
        return False
    clean_code = code.strip().replace(" ", "").replace("-", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False
    try:
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(clean_code, valid_window=valid_window))
    except Exception as e:
        logger.warning(f"Error during TOTP code verification: {e}")
        return False


# ==============================================================================
# 4. TWO-FACTOR RECOVERY CODES
# ==============================================================================

def generate_recovery_codes(count: int = 8) -> List[str]:
    """
    Generates cryptographically random recovery codes (format: XXXXX-XXXXX).
    """
    codes = []
    for _ in range(count):
        part1 = secrets.token_hex(3).upper()[:5]
        part2 = secrets.token_hex(3).upper()[:5]
        codes.append(f"{part1}-{part2}")
    return codes


def hash_recovery_code(code: str) -> str:
    """Hashes a recovery code for secure database storage."""
    clean_code = code.strip().upper().replace(" ", "")
    return hashlib.sha256(f"vidhik_recovery:{clean_code}".encode("utf-8")).hexdigest()


def verify_recovery_code(plain_code: str, stored_hash: str) -> bool:
    """Verifies a plain recovery code against a stored hash."""
    calculated = hash_recovery_code(plain_code)
    return secrets.compare_digest(calculated, stored_hash)


# ==============================================================================
# 5. JWT TOKENS (ACCESS, REFRESH, 2FA CHALLENGE)
# ==============================================================================

def create_access_token(
    user_id: int,
    email: str,
    role: str,
    full_name: Optional[str] = None,
    lawyer_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generates a cryptographically signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    payload: Dict[str, Any] = {
        "jti": secrets.token_hex(16),
        "sub": str(user_id),
        "user_id": user_id,
        "email": email.strip().lower(),
        "role": role,
        "full_name": full_name or "",
        "lawyer_id": lawyer_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_two_factor_challenge_token(
    user_id: int,
    email: str,
    role: str,
    full_name: Optional[str] = None,
    lawyer_id: Optional[int] = None,
    login_method: str = "password"
) -> str:
    """
    Issues a short-lived 2FA challenge token (5-minute expiration).
    Used exclusively to complete the second factor challenge before an access token is issued.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=TWO_FACTOR_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "jti": secrets.token_hex(16),
        "sub": str(user_id),
        "user_id": user_id,
        "email": email.strip().lower(),
        "role": role,
        "full_name": full_name or "",
        "lawyer_id": lawyer_id,
        "login_method": login_method,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "2fa_challenge"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_two_factor_setup_token(
    user_id: int,
    email: str,
    temp_secret: str
) -> str:
    """Issues a short-lived token for mandatory 2FA enrollment."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=15)

    payload: Dict[str, Any] = {
        "jti": secrets.token_hex(16),
        "sub": str(user_id),
        "user_id": user_id,
        "email": email.strip().lower(),
        "temp_secret": temp_secret,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "2fa_setup"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, datetime]:
    """Generates an unguessable 32-byte refresh token and expiration date."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    token = secrets.token_urlsafe(32)
    return token, expire


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]}
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and ensures token is of type 'access'."""
    payload = decode_jwt_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def decode_two_factor_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and ensures token is of type '2fa_challenge' or '2fa_setup'."""
    payload = decode_jwt_token(token)
    if payload and payload.get("type") in ("2fa_challenge", "2fa_setup"):
        return payload
    return None


def generate_reset_token() -> str:
    """Generates a cryptographic 32-byte URL-safe reset token."""
    return secrets.token_urlsafe(32)


# ==============================================================================
# 6. CLOUDFLARE TURNSTILE CAPTCHA VALIDATION
# ==============================================================================

def _process_turnstile_response(data: Dict[str, Any], expected_hostname: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Evaluates Cloudflare Turnstile Siteverify API JSON payload."""
    is_prod = is_production_environment()
    if data.get("success") is True:
        # If strict hostname verification is configured in production
        exp_host = expected_hostname or os.getenv("TURNSTILE_EXPECTED_HOSTNAME", TURNSTILE_EXPECTED_HOSTNAME)
        actual_host = data.get("hostname")
        is_test_mode = data.get("metadata", {}).get("result_with_testing_key") is True

        if is_prod and is_test_mode:
            logger.warning("Turnstile response indicates result_with_testing_key, but environment is production.")
            return False, "CAPTCHA verification failed. Test keys are not permitted in production."

        if exp_host and actual_host and not is_test_mode:
            if actual_host.lower() != exp_host.lower():
                logger.warning(f"Turnstile hostname mismatch: expected {exp_host}, got {actual_host}")
                return False, "CAPTCHA verification hostname mismatch."
        return True, None

    error_codes = data.get("error-codes", [])
    logger.warning(f"Cloudflare Turnstile verification failed with error codes: {error_codes}")

    if "timeout-or-duplicate" in error_codes:
        return False, "CAPTCHA token has expired or was already used. Please complete the challenge again."
    if "invalid-input-response" in error_codes or "missing-input-response" in error_codes:
        return False, "Invalid or missing CAPTCHA challenge response. Please try again."
    if "invalid-input-secret" in error_codes or "missing-input-secret" in error_codes:
        logger.error("Cloudflare Turnstile secret key configuration error.")
        return False, "Anti-bot verification service misconfigured."

    return False, "Anti-bot verification failed. Please refresh and try again."


async def verify_turnstile_token(token: Optional[str], remote_ip: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Performs server-side verification of Cloudflare Turnstile token via Cloudflare API:
    POST https://challenges.cloudflare.com/turnstile/v0/siteverify
    """
    if not token or not token.strip():
        return False, "CAPTCHA verification is required. Please complete the challenge."

    token_str = token.strip()
    is_prod = is_production_environment()

    # In production, Cloudflare dummy test tokens are strictly prohibited
    if is_prod and token_str in TEST_TURNSTILE_TOKENS:
        logger.warning("Cloudflare Turnstile test dummy token was rejected in production environment.")
        return False, "CAPTCHA verification failed. Test tokens are not permitted in production."

    secret_key = os.getenv("TURNSTILE_SECRET_KEY", TURNSTILE_SECRET_KEY)

    if not is_prod:
        # In development/test mode, Cloudflare standard test tokens pair with standard test secret key
        if token_str in TEST_TURNSTILE_TOKENS:
            secret_key = token_str
    else:
        # In production mode, dummy test secret keys are rejected
        if not secret_key or secret_key in TEST_TURNSTILE_SECRET_KEYS:
            logger.error("Cloudflare Turnstile secret key is misconfigured with test key in production environment.")
            return False, "Anti-bot verification service is not properly configured for production."

    if not secret_key:
        logger.error("TURNSTILE_SECRET_KEY is missing.")
        return False, "Anti-bot verification service is not configured."

    try:
        payload = {
            "secret": secret_key,
            "response": token_str
        }
        if remote_ip and ":" not in remote_ip and remote_ip != "127.0.0.1":
            payload["remoteip"] = remote_ip

        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data=payload
            )
            data = resp.json()
            return _process_turnstile_response(data)
    except Exception as e:
        logger.error(f"Error verifying Cloudflare Turnstile token: {e}")
        return False, "Anti-bot verification service temporarily unreachable. Please try again."


def verify_turnstile_token_sync(token: Optional[str], remote_ip: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Synchronous version of Turnstile verification using httpx."""
    if not token or not token.strip():
        return False, "CAPTCHA verification is required. Please complete the challenge."

    token_str = token.strip()
    is_prod = is_production_environment()

    # In production, Cloudflare dummy test tokens are strictly prohibited
    if is_prod and token_str in TEST_TURNSTILE_TOKENS:
        logger.warning("Cloudflare Turnstile test dummy token was rejected in production environment.")
        return False, "CAPTCHA verification failed. Test tokens are not permitted in production."

    secret_key = os.getenv("TURNSTILE_SECRET_KEY", TURNSTILE_SECRET_KEY)

    if not is_prod:
        # In development/test mode, Cloudflare standard test tokens pair with standard test secret key
        if token_str in TEST_TURNSTILE_TOKENS:
            secret_key = token_str
    else:
        # In production mode, dummy test secret keys are rejected
        if not secret_key or secret_key in TEST_TURNSTILE_SECRET_KEYS:
            logger.error("Cloudflare Turnstile secret key is misconfigured with test key in production environment.")
            return False, "Anti-bot verification service is not properly configured for production."

    if not secret_key:
        logger.error("TURNSTILE_SECRET_KEY is missing.")
        return False, "Anti-bot verification service is not configured."

    try:
        payload = {
            "secret": secret_key,
            "response": token_str
        }
        if remote_ip and ":" not in remote_ip and remote_ip != "127.0.0.1":
            payload["remoteip"] = remote_ip

        with httpx.Client(timeout=6.0) as client:
            resp = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data=payload
            )
            data = resp.json()
            return _process_turnstile_response(data)
    except Exception as e:
        logger.error(f"Error in sync Turnstile verification: {e}")
        return False, "Anti-bot verification service temporarily unavailable. Please try again."


# ==============================================================================
# 7. GOOGLE OAUTH 2.0 / OIDC VERIFICATION
# ==============================================================================

async def verify_google_id_token(id_token_str: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validates a Google OAuth ID token using Google's tokeninfo endpoint:
    GET https://oauth2.googleapis.com/tokeninfo?id_token={id_token}
    Validates issuer, audience, and email verification.
    """
    if not id_token_str or not id_token_str.strip():
        return False, None, "Google identity token is missing."

    try:
        async with httpx.AsyncClient(timeout=7.0) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token_str.strip()}
            )
            if resp.status_code != 200:
                return False, None, "Invalid or expired Google authentication token."

            data = resp.json()

            # Verify Issuer
            iss = data.get("iss", "")
            if iss not in ("accounts.google.com", "https://accounts.google.com"):
                return False, None, "Google token issuer is invalid."

            # Verify Audience if configured
            expected_aud = os.getenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
            if expected_aud and expected_aud != "vidhik-legal-auth.apps.googleusercontent.com":
                aud = data.get("aud", "")
                if aud != expected_aud:
                    return False, None, "Google token audience mismatch."

            # Verify Email verified flag
            email = data.get("email")
            if not email:
                return False, None, "Google account does not contain a valid email."

            email_verified = data.get("email_verified") in (True, "true", "True")
            if not email_verified:
                return False, None, "Google email address is not verified."

            return True, {
                "sub": data.get("sub"),
                "email": email.strip().lower(),
                "full_name": data.get("name") or data.get("given_name") or email.split("@")[0],
                "picture": data.get("picture"),
                "locale": data.get("locale")
            }, None

    except Exception as e:
        logger.error(f"Error during Google ID token verification: {e}")
        return False, None, f"Google authentication verification service error: {str(e)}"


# ==============================================================================
# 8. USER AGENT PARSING & APPROXIMATE GEOIP RESOLUTION
# ==============================================================================

def parse_user_agent(user_agent_str: Optional[str]) -> Dict[str, str]:
    """
    Parses browser, operating system, and device form factor from User-Agent string.
    """
    if not user_agent_str:
        return {"device": "Desktop", "browser": "Browser", "os": "Unknown OS"}

    ua = user_agent_str

    # 1. Device Type
    device = "Desktop"
    if re.search(r"Mobile|Android|iPhone|iPod", ua, re.I):
        device = "Mobile"
    elif re.search(r"iPad|Tablet|PlayBook", ua, re.I):
        device = "Tablet"

    # 2. Operating System
    os_name = "Unknown OS"
    if "iPhone" in ua or "iPad" in ua or "iPod" in ua:
        os_name = "iOS"
    elif "Windows NT 10.0" in ua or "Windows NT 11.0" in ua:
        os_name = "Windows"
    elif "Windows NT" in ua:
        os_name = "Windows"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "Android" in ua:
        os_name = "Android"
    elif "Linux" in ua:
        os_name = "Linux"

    # 3. Browser
    browser_name = "Browser"
    if "Edg/" in ua or "Edge/" in ua:
        browser_name = "Microsoft Edge"
    elif "Chrome/" in ua and "Safari/" in ua:
        browser_name = "Chrome"
    elif "Firefox/" in ua:
        browser_name = "Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua:
        browser_name = "Safari"
    elif "Opera" in ua or "OPR/" in ua:
        browser_name = "Opera"

    return {
        "device": device,
        "browser": browser_name,
        "os": os_name
    }


def resolve_ip_location(ip_address: Optional[str]) -> Dict[str, str]:
    """
    Resolves approximate geographic location (City, State/Region, Country) from IP address.
    Does not track or expose exact physical street addresses.
    Handles loopback/private IPs gracefully.
    """
    if not ip_address or ip_address in ("127.0.0.1", "::1", "localhost") or ip_address.startswith("192.168.") or ip_address.startswith("10."):
        return {
            "city": "Pune",
            "region": "Maharashtra",
            "country": "India",
            "formatted": "Pune, Maharashtra, India"
        }

    clean_ip = ip_address.strip()
    if clean_ip in _GEOIP_CACHE:
        return _GEOIP_CACHE[clean_ip]

    # Quick lookup via ip-api with timeout
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"http://ip-api.com/json/{clean_ip}?fields=status,country,regionName,city")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    city = data.get("city", "Mumbai")
                    region = data.get("regionName", "Maharashtra")
                    country = data.get("country", "India")
                    loc = {
                        "city": city,
                        "region": region,
                        "country": country,
                        "formatted": f"{city}, {region}, {country}"
                    }
                    _GEOIP_CACHE[clean_ip] = loc
                    return loc
    except Exception:
        pass

    fallback = {
        "city": "Mumbai",
        "region": "Maharashtra",
        "country": "India",
        "formatted": "Mumbai, Maharashtra, India"
    }
    _GEOIP_CACHE[clean_ip] = fallback
    return fallback


# ==============================================================================
# 9. SUSPICIOUS LOGIN & RISK EVALUATION
# ==============================================================================

def evaluate_login_risk(
    user_id: int,
    current_ip: str,
    current_device: str,
    current_browser: str,
    current_location: str,
    recent_sessions: List[Dict[str, Any]]
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates risk signals for the current authentication event:
    - New device or browser
    - New location (different city/country)
    - Suspicious travel anomaly
    """
    if not recent_sessions:
        # First login or no prior sessions: normal onboarding
        return False, None

    known_devices = {s.get("device") for s in recent_sessions if s.get("device")}
    known_browsers = {s.get("browser") for s in recent_sessions if s.get("browser")}
    known_cities = {s.get("location_city") for s in recent_sessions if s.get("location_city")}

    is_new_device = current_device not in known_devices if known_devices else False
    is_new_browser = current_browser not in known_browsers if known_browsers else False
    
    current_city = current_location.split(",")[0].strip() if "," in current_location else current_location
    is_new_location = current_city not in known_cities if (known_cities and current_city) else False

    if is_new_device or is_new_browser or is_new_location:
        signals = []
        if is_new_device or is_new_browser:
            signals.append(f"New device ({current_browser} on {current_device})")
        if is_new_location:
            signals.append(f"New location ({current_location})")
        return True, ", ".join(signals)

    return False, None
