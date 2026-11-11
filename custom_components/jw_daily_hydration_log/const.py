"""Constants for jwDaily Hydration Log (a distinct MIT-licensed fork)."""
from __future__ import annotations

DOMAIN = 'jw_daily_hydration_log'
NAME = 'jwDaily Hydration Log'
VERSION = '1.1.0-beta.23'
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

# The historical beta.22 palette is intentionally retained until a profile
# explicitly saves a per-liquid override. Keep in sync with the card JS.
LIQUID_PALETTE = ('#39A8DE', '#F2A34A', '#67B69A', '#9280D0',
                  '#DD7BA6', '#79A2E7', '#C6AD63', '#82B5CB')


def default_liquid_color(liquid_id: str, name: str = '') -> str:
    key = str(liquid_id or '').strip().lower()
    label = str(name or liquid_id or '').strip().lower()
    both = key + ' ' + label
    if 'water' in both and ('beker' in both or 'cup' in both):
        return '#9280D0'
    if 'water' in both and ('glas' in both or 'glass' in both):
        return '#DD7BA6'
    for patterns, color in (
        (('coffee', 'koffie'), '#F2A34A'), (('tea', 'thee'), '#67B69A'),
        (('milk', 'melk'), '#39A8DE'), (('orange', 'sinaasappel'), '#D45A38'),
        (('wine', 'wijn'), '#C6AD63'), (('soup', 'soep'), '#82B5CB'),
    ):
        if any(word in both for word in patterns):
            return color
    if key == 'water' or label == 'water':
        return '#79A2E7'
    if key == 'other' or label in ('other', 'overige'):
        return '#B89D83'
    hash_value = 2166136261
    for char in key:
        # JS for..of iterates code points but charCodeAt(0) returns a
        # UTF-16 unit for astral symbols; stable liquid IDs are ASCII.
        code = ord(char)
        if code > 0xFFFF:
            code = 0xD800 + ((code - 0x10000) >> 10)
        hash_value = ((hash_value ^ code) * 16777619) & 0xFFFFFFFF
    return LIQUID_PALETTE[hash_value % len(LIQUID_PALETTE)]
