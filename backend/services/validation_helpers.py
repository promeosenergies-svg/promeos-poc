"""
PROMEOS - Format Validation Helpers
Industrial-grade validators for French business identifiers.
"""
import re


def _luhn_checksum(digits: str) -> bool:
    """Standard Luhn mod-10 checksum validation."""
    nums = [int(d) for d in digits]
    for i in range(len(nums) - 2, -1, -2):
        nums[i] *= 2
        if nums[i] > 9:
            nums[i] -= 9
    return sum(nums) % 10 == 0


def is_valid_siren(value: str) -> bool:
    """Validate French SIREN: exactly 9 digits + Luhn checksum."""
    if not value:
        return False
    v = value.strip()
    if not re.fullmatch(r"\d{9}", v):
        return False
    return _luhn_checksum(v)


def is_valid_siret(value: str) -> bool:
    """Validate French SIRET: exactly 14 digits + Luhn checksum."""
    if not value:
        return False
    v = value.strip()
    if not re.fullmatch(r"\d{14}", v):
        return False
    return _luhn_checksum(v)


def is_valid_meter_id(value: str) -> bool:
    """Validate PRM/PCE delivery point identifier: exactly 14 digits."""
    if not value:
        return False
    v = value.strip()
    return bool(re.fullmatch(r"\d{14}", v))


def is_valid_postal_code(value: str) -> bool:
    """Validate French postal code: 5 digits, valid department (01-95, 97, 98)."""
    if not value:
        return False
    v = value.strip()
    if not re.fullmatch(r"\d{5}", v):
        return False
    dept = int(v[:2])
    if dept == 0:
        return False
    if dept <= 95:
        return True
    if dept in (97, 98):
        return True
    return False


def is_valid_date_str(value: str) -> bool:
    """Validate date string: YYYY-MM-DD or DD/MM/YYYY."""
    if not value:
        return False
    v = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        y, m, d = int(v[:4]), int(v[5:7]), int(v[8:10])
        return 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):
        d, m, y = int(v[:2]), int(v[3:5]), int(v[6:10])
        return 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31
    return False
