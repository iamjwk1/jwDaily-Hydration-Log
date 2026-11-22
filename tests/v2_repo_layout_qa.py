"""v2.0.0: repository documentation is organized and root README is current."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
assert json.loads((root/"custom_components/jw_daily_hydration_log/manifest.json").read_text())["version"]=="2.0.0"
top=sorted(p.name for p in root.glob("*.md"))
assert top==["README.md"],top
for item in ("docs/CHANGELOG.md","docs/RELEASE_NOTES.md","docs/USER_GUIDE.md",
             "docs/releases/v2.0.0.md","docs/archive/INDEX.md",
             "docs/archive/README_PRE_V2.md",
             "docs/archive/releases/RELEASE_NOTES_v1.1.0-beta.48.md",
             "docs/archive/releases/RELEASE_NOTES_v1.5.1-beta.4.md",
             "docs/examples/apexcharts.md"):
    assert (root/item).is_file(),item
readme=(root/"README.md").read_text()
for required in ("## What can it do?","## Installation (HACS)","## Interface at a glance",
                 "## History, daily snapshots and backups","docs/RELEASE_NOTES.md",
                 "docs/USER_GUIDE.md","v2.0.0"):
    assert required in readme,required
assert "Historical release information (archive only)" not in readme
active=sorted(p.name for p in (root/".github/workflows").glob("*.yml"))
assert active==["ci.yml","publish-v2.0.0.yml","validate.yml"],active
archived=list((root/"docs/archive/workflows").glob("*.yml"))
assert len(archived)>=50,len(archived)
releasefiles=list((root/"docs/archive/releases").glob("RELEASE_NOTES_*.md"))
assert len(releasefiles)>=49,len(releasefiles)
assert "RELEASE_NOTES_" not in " ".join(top)
print("V2_REPOSITORY_LAYOUT_QA_PASS",len(releasefiles),"releases",len(archived),"retired workflows")
# Repository layout audit marker 1
