"""Prevent mismatched card/backend versions in jwDaily Hydration Log."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
component = root / 'custom_components/jw_daily_hydration_log'
manifest = json.loads((component / 'manifest.json').read_text(encoding='utf-8'))
version = manifest['version']
constants = (component / 'const.py').read_text(encoding='utf-8')
card = (component / 'www/jwdaily-hydration-log-card.js').read_text(encoding='utf-8')
assert version == '1.1.0-beta.47', version
assert f"VERSION = '{version}'" in constants
prefix = "if(info?.version!=='"
guards = [line.strip() for line in card.splitlines() if prefix in line]
assert len(guards) == 1, f'Expected one backend version guard, found {len(guards)}'
assert guards[0].startswith(prefix + version + "')"), f'Backend version guard mismatch: {guards[0]}'
assert f'Frontend v{version} is connected to backend' in card
assert f'<span class="card-version">v{version}</span>' in card
print('BETA39_VERSION_GUARD_QA_PASS', version)
