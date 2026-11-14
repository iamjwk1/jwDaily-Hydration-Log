"""Prevent mismatched card/backend versions in jwDaily Hydration Log."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1]
component = root / 'custom_components/jw_daily_hydration_log'
manifest = json.loads((component / 'manifest.json').read_text(encoding='utf-8'))
version = manifest['version']
constants = (component / 'const.py').read_text(encoding='utf-8')
card = (component / 'www/jwdaily-hydration-log-card.js').read_text(encoding='utf-8')
assert version == '1.1.0-beta.39', version
assert f"VERSION = '{version}'" in constants
matches = re.findall(r"info\\?\\.version!=='([^']+)'", card)
assert matches == [version], f'Card version guard must exactly match manifest: {matches} vs {version}'
assert f'Frontend v{version} is connected to backend' in card
assert f'<span class="card-version">v{version}</span>' in card
print('BETA39_VERSION_GUARD_QA_PASS', version)
