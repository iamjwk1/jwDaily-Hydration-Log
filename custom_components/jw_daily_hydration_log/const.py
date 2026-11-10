"""Constants for jwDaily Hydration Log (a distinct MIT-licensed fork)."""
from __future__ import annotations

DOMAIN = 'jw_daily_hydration_log'
NAME = 'jwDaily Hydration Log'
VERSION = '1.1.0-beta.10'
PLATFORMS = ['sensor', 'number']
ENTITY_PREFIX = 'jwdhl'
EVENT_DRINK = 'jw_daily_hydration_log_drink'
SIGNAL = 'jw_daily_hydration_log_updated_{}'
UNITS = ('mL', 'L', 'fl_oz')
SOURCE_MODES = ('absolute', 'delta', 'sum')
LIQUID_TYPES = ('water', 'coffee', 'tea', 'milk', 'soup', 'wine', 'other')

NASEM_TABLE = ((1,3,None,900),(4,8,None,1200),(9,13,'male',1900),
               (9,13,'female',1600),(14,18,'male',2600),(14,18,'female',1800),
               (19,200,'male',3000),(19,200,'female',2200))


def target_ml(age: int, gender: str, pregnancy: bool = False, lactation: bool = False) -> int:
    if lactation:
        return 3000
    if pregnancy:
        return 2400
    for min_age, max_age, sex, target in NASEM_TABLE:
        if min_age <= age <= max_age and (sex is None or sex == gender):
            return target
    return 2200


def to_ml(value: float, unit: str) -> float:
    if unit == 'L':
        return value * 1000
    if unit == 'fl_oz':
        return value * 29.5735
    return value


def from_ml(value: float, unit: str) -> float:
    if unit == 'L':
        return value / 1000
    if unit == 'fl_oz':
        return value / 29.5735
    return value


def safe_amount(value: object, unit: str) -> float:
    """Reject NaN, infinity and non-positive drinks (unlike upstream)."""
    import math
    if unit not in UNITS:
        raise ValueError(f'Unsupported unit: {unit}')
    amount = float(value)
    if not math.isfinite(amount) or amount <= 0 or to_ml(amount,unit) > 100000:
        raise ValueError('Volume must be a finite positive number of at most 100000 mL')
    return to_ml(amount, unit)
