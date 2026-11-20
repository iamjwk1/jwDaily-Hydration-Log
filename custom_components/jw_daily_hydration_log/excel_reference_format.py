"""Sanitized style/column metadata from the approved six-sheet Excel reference.

Contains ONLY shared OOXML style/theme definitions and column-width geometry.
Never includes a workbook data cell, original user value, profile, drink event,
icon image, image relationship or personal information.
"""
from __future__ import annotations
import base64, zlib

REFERENCE_STYLES = zlib.decompress(base64.b64decode("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"))
REFERENCE_THEME = zlib.decompress(base64.b64decode("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"))
REFERENCE_COLS = {1: '<cols><col min="1" max="1" width="4" customWidth="1"/><col min="2" max="2" width="19" customWidth="1"/><col '
    'min="3" max="3" width="16" customWidth="1"/><col min="4" max="4" width="6" customWidth="1"/><col min="5" max="6" '
    'width="9" customWidth="1"/><col min="7" max="7" width="17" customWidth="1"/><col min="8" max="8" width="11" '
    'customWidth="1"/><col min="9" max="9" width="25" customWidth="1"/></cols>',
 2: '<cols><col min="1" max="1" width="4.28515625" customWidth="1"/><col min="2" max="2" width="16" '
    'customWidth="1"/><col min="3" max="3" width="15" customWidth="1"/><col min="4" max="4" width="7" '
    'customWidth="1"/><col min="5" max="5" width="9" customWidth="1"/><col min="6" max="6" width="6" '
    'customWidth="1"/><col min="7" max="7" width="10" customWidth="1"/><col min="8" max="8" width="9" '
    'customWidth="1"/><col min="9" max="9" width="11" customWidth="1"/><col min="10" max="10" width="6" '
    'customWidth="1"/><col min="11" max="11" width="8.92578125" bestFit="1" customWidth="1"/><col min="12" max="12" '
    'width="9" bestFit="1" customWidth="1"/><col min="13" max="13" width="9.92578125" bestFit="1" '
    'customWidth="1"/><col min="14" max="14" width="10" customWidth="1"/><col min="15" max="15" width="17.35546875" '
    'bestFit="1" customWidth="1"/><col min="16" max="16" width="8.7109375" bestFit="1" customWidth="1"/><col min="17" '
    'max="17" width="9.2109375" bestFit="1" customWidth="1"/><col min="18" max="18" width="11.35546875" bestFit="1" '
    'customWidth="1"/></cols>',
 3: '<cols><col min="1" max="1" width="3.2109375" customWidth="1"/><col min="2" max="3" width="16" '
    'customWidth="1"/><col min="4" max="4" width="17.42578125" customWidth="1"/><col min="5" max="5" '
    'width="16.2109375" style="27" customWidth="1"/><col min="6" max="6" width="7.7109375" style="34" '
    'customWidth="1"/><col min="7" max="7" width="12" style="34" bestFit="1" customWidth="1"/><col min="8" max="8" '
    'width="13" style="34" customWidth="1"/><col min="9" max="9" width="8.2109375" style="34" customWidth="1"/><col '
    'min="10" max="10" width="8.2109375" customWidth="1"/><col min="11" max="11" width="9.2109375" style="27" '
    'customWidth="1"/><col min="12" max="12" width="8.28515625" style="34" bestFit="1" customWidth="1"/><col min="13" '
    'max="13" width="7.640625" style="34" customWidth="1"/></cols>',
 4: '<cols><col min="1" max="1" width="3.7109375" customWidth="1"/><col min="2" max="3" width="16" '
    'customWidth="1"/><col min="4" max="4" width="16.28515625" customWidth="1"/><col min="5" max="5" width="12" '
    'customWidth="1"/><col min="6" max="6" width="18.640625" customWidth="1"/><col min="7" max="7" width="7.2109375" '
    'customWidth="1"/><col min="8" max="8" width="7.7109375" customWidth="1"/><col min="9" max="9" width="9.78515625" '
    'bestFit="1" customWidth="1"/><col min="10" max="10" width="10.640625" bestFit="1" customWidth="1"/><col min="11" '
    'max="11" width="25" customWidth="1"/><col min="12" max="12" width="20" customWidth="1"/><col min="13" max="13" '
    'width="24" customWidth="1"/><col min="14" max="14" width="15" customWidth="1"/><col min="15" max="16" width="24" '
    'customWidth="1"/></cols>',
 5: '<cols><col min="1" max="1" width="3.7109375" customWidth="1"/><col min="2" max="2" width="16" '
    'customWidth="1"/><col min="3" max="3" width="21.5" customWidth="1"/><col min="4" max="4" width="23" bestFit="1" '
    'customWidth="1"/><col min="5" max="5" width="14.640625" bestFit="1" customWidth="1"/><col min="6" max="6" '
    'width="11.2109375" customWidth="1"/><col min="7" max="7" width="10.640625" bestFit="1" customWidth="1"/><col '
    'min="8" max="8" width="15.640625" customWidth="1"/><col min="9" max="9" width="17.42578125" customWidth="1"/><col '
    'min="10" max="10" width="9.78515625" bestFit="1" customWidth="1"/><col min="11" max="11" width="22" '
    'customWidth="1"/><col min="12" max="12" width="18.0703125" customWidth="1"/><col min="13" max="13" width="19" '
    'customWidth="1"/><col min="14" max="14" width="13.42578125" bestFit="1" customWidth="1"/></cols>',
 6: '<cols><col min="1" max="1" width="3.7109375" customWidth="1"/><col min="2" max="3" width="16" '
    'customWidth="1"/><col min="4" max="4" width="8" bestFit="1" customWidth="1"/><col min="5" max="5" '
    'width="11.140625" bestFit="1" customWidth="1"/><col min="6" max="6" width="8.42578125" bestFit="1" '
    'customWidth="1"/><col min="7" max="7" width="17.5" bestFit="1" customWidth="1"/><col min="8" max="8" width="20.5" '
    'bestFit="1" customWidth="1"/><col min="9" max="9" width="21.140625" bestFit="1" customWidth="1"/><col min="10" '
    'max="10" width="25" customWidth="1"/><col min="11" max="11" width="20" customWidth="1"/><col min="12" max="12" '
    'width="24" customWidth="1"/><col min="13" max="13" width="15" customWidth="1"/><col min="14" max="15" width="24" '
    'customWidth="1"/></cols>'}
REFERENCE_LIQUID_WIDTHS = {'koffie': 9.92578125,
 'melk': 9.0,
 'overige': 11.35546875,
 'sinasappelsap': 17.35546875,
 'soep': 9.2109375,
 'thee': 8.92578125,
 'water': 10.0,
 'wijn': 8.7109375}