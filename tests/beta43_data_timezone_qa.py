"""Beta43: imports must use HA-local day rather than the OS/UTC calendar date."""
from datetime import date
from pathlib import Path
import importlib.util
root=Path(__file__).resolve().parents[1]
path=root/"custom_components"/"jw_daily_hydration_log"/"data_io.py"
spec=importlib.util.spec_from_file_location("audit_data_io",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
local_day=date(2026,11,16)
utc_day=date(2026,11,15)
assert module._date("2026-11-16",today=local_day)=="2026-11-16"
assert module._iso("2026-11-16T00:12:00+01:00",today=local_day)=="2026-11-16T00:12:00+01:00"
for method,value in ((module._date,"2026-11-16"),(module._iso,"2026-11-16T00:12:00+01:00")):
    try:method(value,today=utc_day)
    except ValueError:pass
    else:raise AssertionError("Validator unexpectedly ignored the earlier source-system date")
try:module._date("2026-11-17",today=local_day)
except ValueError:pass
else:raise AssertionError("Tomorrow was not rejected")
print("BETA43_HA_LOCAL_IMPORT_DATE_PASS")
