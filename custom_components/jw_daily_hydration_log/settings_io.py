"""Strict, non-destructive v2 settings exchange. No personal drink records exported.

This module is deliberately independent of Home Assistant for offline QA.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from copy import deepcopy
from typing import Any

FORMAT = 'jwDaily-Hydration-Log-settings'
SCHEMA = 2
FIELDS = ('liquid_overrides', 'custom_liquid_types', 'liquid_colors',
          'hidden_builtin_liquids', 'liquid_order',
          'cup_types', 'quick_buttons', 'target_override_ml')
PROFILE_FIELDS = ('age','gender','unit')
BUILTINS = {'water','coffee','tea','milk','soup','wine','other'}
HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
MDI = re.compile(r'^mdi:[a-z0-9-]{2,70}$')
MAX_BYTES = 256_000


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(',', ':')).encode('utf-8')


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def extract(coordinator) -> dict:
    """No history, sensor data, drink records, entity IDs or secrets."""
    return {key: deepcopy(getattr(coordinator, key)) for key in FIELDS}


def export_payload(coordinator) -> dict:
    return dict(format=FORMAT, schema=SCHEMA,
                source_profile=dict(name=coordinator.name, slug=coordinator.slug),
                profile_preferences={key: getattr(coordinator, key) for key in PROFILE_FIELDS},
                settings=extract(coordinator))


def _name(v, label):
    if not isinstance(v, str) or not (1 <= len(v.strip()) <= 60) or any(ord(c)<32 for c in v):
        raise ValueError(label+' must contain 1–60 printable characters')
    return v.strip()


def _list(value, label, limit):
    if not isinstance(value, list) or len(value)>limit:
        raise ValueError(label+' must be an array of at most '+str(limit))
    return value


def _ids(rows, label):
    ids=[]
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(label+' contains a non-object')
        ident = row.get('id')
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_\-]{1,80}',ident):
            raise ValueError(label+' contains an invalid ID')
        ids.append(ident)
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate IDs in '+label)
    return ids


def _number(v, label, zero=False):
    if type(v) not in (int,float) or not math.isfinite(v) or v<0 or (not zero and v==0) or v>100000:
        raise ValueError(label+' must be a finite value between '+('0' if zero else '0.01')+' and 100000 mL')
    return float(v)


def validate_payload(raw: dict, *, existing_legacy_ids: set[str] | None=None,
                     include_mappings: bool = False) -> dict:
    """Return a deep-copied, completely verified settings dictionary. No writes."""
    if not isinstance(raw,dict) or raw.get('format')!=FORMAT or raw.get('schema') not in (1,2):
        raise ValueError('Unknown settings format or schema version')
    if len(canonical(raw))>MAX_BYTES:
        raise ValueError('Settings file exceeds 256 KB')
    settings=raw.get('settings')
    if not isinstance(settings,dict):
        raise ValueError('Malformed settings payload')
    historical={'volume_buttons','legacy_mappings','legacy_cup_defaults','conversion_state'}
    if any(k not in FIELDS and not (raw['schema']==1 and k in historical) for k in settings):
        raise ValueError('Unknown settings field')
    if any(key not in settings for key in FIELDS):
        raise ValueError('Incomplete settings payload')
    s={key:deepcopy(settings[key]) for key in FIELDS}
    # Safe compatibility import for beta.29 Settings/Full Backup. Legacy aliases
    # whose own IDs were already migrated disappear from the active catalogue;
    # a matching schema-v2 Data file must still validate its canonical references.
    if raw.get('schema')==1:
        retired=set((settings.get('legacy_mappings') or {}).keys())
        quick_sources={q.get('liquid_type_id') for q in s.get('quick_buttons', []) if isinstance(q, dict)}
        retired -= quick_sources
        s['custom_liquid_types']=[v for v in s['custom_liquid_types'] if v.get('id') not in retired]
        s['liquid_order']=[ident for ident in s['liquid_order'] if ident not in retired]
        s['liquid_colors']={k:v for k,v in s['liquid_colors'].items() if k not in retired}
        s['custom_liquid_types']=[{k:v for k,v in typ.items() if k!='default_volume_ml'} for typ in s['custom_liquid_types']]
        s['liquid_overrides']={k:{a:b for a,b in v.items() if a!='default_volume_ml'} for k,v in s['liquid_overrides'].items()}
    all_ids=set(BUILTINS)
    custom=_list(s['custom_liquid_types'],'Custom liquids',30)
    liquid_ids=_ids(custom,'Custom liquids')
    if set(liquid_ids)&BUILTINS:
        raise ValueError('Custom liquid collides with a built-in ID')
    all_ids.update(liquid_ids)
    for t in custom:
        _name(t.get('name'),'Liquid name')
        if t.get('icon_mdi') and not MDI.fullmatch(t['icon_mdi']):
            raise ValueError('Invalid liquid icon')
        if t.get('icon_svg') and (not isinstance(t['icon_svg'],str) or len(t['icon_svg'].encode())>16000):
            raise ValueError('Invalid liquid SVG')
        if t.get('default_volume_ml') is not None:_number(t['default_volume_ml'],'Liquid volume')
    overrides=s['liquid_overrides']
    if not isinstance(overrides,dict) or not set(overrides)<=BUILTINS or not all(isinstance(v,dict) for v in overrides.values()):
        raise ValueError('Invalid built-in liquid overrides')
    for override in overrides.values():
        if 'name' in override:_name(override['name'],'Liquid name')
        if override.get('icon_mdi') and not MDI.fullmatch(override['icon_mdi']):raise ValueError('Invalid built-in icon')
    colors=s['liquid_colors']
    if not isinstance(colors,dict) or len(colors)>70 or not all(isinstance(k,str) and HEX.fullmatch(v) for k,v in colors.items()):
        raise ValueError('Invalid hex colors')
    s['liquid_colors']={k:v.upper() for k,v in colors.items()}
    hidden=_list(s['hidden_builtin_liquids'],'Hidden built-in liquids',7)
    if len(set(hidden))!=len(hidden) or not set(hidden)<=BUILTINS:raise ValueError('Invalid hidden liquid IDs')
    order=_list(s['liquid_order'],'Liquid order',37)
    if len(set(order))!=len(order) or not set(order)<=all_ids:raise ValueError('Invalid liquid order')
    cups=_list(s['cup_types'],'Cup types',40)
    cup_ids=set(_ids(cups,'Cup types'))
    cup_names=set()
    for cup in cups:
        name=_name(cup.get('name'),'Cup name')
        if name.casefold() in cup_names:raise ValueError('Duplicate cup names')
        cup_names.add(name.casefold())
        _number(cup.get('default_volume_ml'),'Cup volume')
        if cup.get('icon_mdi') and not MDI.fullmatch(cup['icon_mdi']):raise ValueError('Invalid Cup icon')
        if type(cup.get('hidden',False)) is not bool:raise ValueError('Invalid cup visibility')
    quick=_list(s['quick_buttons'],'Quick buttons',48)
    _ids(quick,'Quick buttons')
    combos=set()
    for button in quick:
        lid,cid=button.get('liquid_type_id'),button.get('cup_type_id')
        if lid not in all_ids or cid not in cup_ids:raise ValueError('Quick button refers to an unknown Liquid or Cup')
        if (lid,cid) in combos:raise ValueError('Duplicate Liquid/Cup Quick button combination')
        combos.add((lid,cid))
        if button.get('icon_mdi') and not MDI.fullmatch(button['icon_mdi']):raise ValueError('Invalid Quick button icon')
        if button.get('label_mode','automatic') not in ('automatic','custom'):raise ValueError('Invalid button label mode')
        if button.get('label_mode')=='custom':_name(button.get('custom_label'),'Custom button label')
        if type(button.get('hidden',False)) is not bool:raise ValueError('Invalid button visibility')
    _number(s['target_override_ml'],'Target override',zero=True)
    return s


def parse_settings_json(contents: str) -> dict:
    if not isinstance(contents,str) or len(contents.encode('utf-8'))>MAX_BYTES:
        raise ValueError('Settings JSON must be at most 256 KB')
    def no_duplicates(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON setting key')
            result[key]=value
        return result
    try:return json.loads(contents,object_pairs_hook=no_duplicates,
                          parse_constant=lambda s:(_ for _ in ()).throw(ValueError('Invalid numeric value')))
    except (TypeError,json.JSONDecodeError) as e:raise ValueError('Invalid settings JSON') from e


def settings_preview(coordinator, settings: dict) -> dict:
    current=extract(coordinator)
    return dict(profile=coordinator.name,profile_slug=coordinator.slug,
                old_revision=digest(current),new_revision=digest(settings),
                counts=dict(liquids=len(settings['custom_liquid_types'])+len(BUILTINS),
                            cups=len(settings['cup_types']),quick_buttons=len(settings['quick_buttons'])),
                changes=[key for key in FIELDS if current[key]!=settings[key]],
                history_unchanged=True,drink_count=sum(r.get('kind')=='drink' for r in coordinator.records))