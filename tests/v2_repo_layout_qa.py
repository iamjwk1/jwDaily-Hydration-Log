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
for required in ("## Purpose and functionality","## Configurable settings","## Installation (HACS)","## Interface at a glance",
                 "## History, daily snapshots and backups","docs/RELEASE_NOTES.md",
                 "docs/USER_GUIDE.md","v2.0.0"):
    assert required in readme,required
assert "## What can it do?" not in readme
assert "No file chosen" not in readme
assert "```yaml\ntype: custom:jwdaily-hydration-log-card" in readme
assert "Data & Backup" in readme
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


# Uploaded user screenshots: exact original PNGs, not scaled, cropped or re-encoded.
import hashlib
import re
import struct
image_specs = {
    "dashboard-main": (725,965,"74179dd2d9b2475f9ea47ade01efefdf4c263e9d085e14df9b076fc01232c94c"),
    "add-drink-quick-buttons": (1165,645,"46fcd4bf1367dac18cdf8ea845c41734933dc9b18d02e80493b68ed09fbc5cbe"),
    "settings-overview": (922,698,"13b7ef1169e1b57485f53e125a58d492f53bb85b3a2cf715d358a5b270c36f12"),
    "manage-profiles": (984,460,"1b9d96a59a6128d1e6cade6afe2a11db6a7272e7084f4fd5f1349f13a68cdf57"),
    "profile-edit": (1299,1086,"c26b36418c170f306236054291cb4f2eeaa5b96e5bee0dfb2544cc842cef1b07"),
    "add-drink-liquid-cup-types": (1166,679,"b4a5bb0652c0c06873a6951ca77d088fe2938d9e93d5cb21caf79f53dd33f3bb"),
    "maintain-liquid-types": (850,997,"d977994f9b4b16691faadec76983b4127bf81b405dfce24ee887da2077fa270f"),
    "maintain-cup-types": (1064,696,"6a4586fb7886918ef39f31ccd17e713feee1aaa35f795cb0718b6b11ae21d8a0"),
    "data-backup": (989,1071,"66000ffe2f9a7dd95f144748413f0320dd9c0412baddfaf1c1637d24f067089b"),
    "quick-buttons-edit": (1147,1026,"c45fd2fccef3f317031e39ff9d2c657aba20856fa3f7d3f1eb0b3d582ce02689"),
    "chart-today-by-hour": (716,684,"94501a0bc091a747a34b91c0203a580ae7e8d16ad7fff1905174e739f0daa9c2"),
    "chart-last-7-days": (722,631,"20bb7073fe141b558a8b79fd3db54facfcc371fd0c598e8f6474ac978e08ba20"),
    "excel-hydration-log": (1696,761,"65809b16be4284ded4559ebf1409fdaf7c4c5d763b2030684c1898cb3abf0bd2"),
    "excel-daily-totals": (2048,655,"63f94d6236eb87637e38adeca3e7db4f53528e7ded088e832355906a80b6ef31"),
}
for stem,(width,height,expected_sha) in image_specs.items():
    png=(root/"docs/images"/f"{stem}.png").read_bytes()
    assert png[:8]==b"\x89PNG\r\n\x1a\n",stem
    assert struct.unpack(">II",png[16:24])==(width,height),stem
    assert hashlib.sha256(png).hexdigest()==expected_sha,stem
    assert len(png)>1000,stem
for doc,filename,prefix in [(readme,"README.md","docs/images/"),
                            ((root/"docs/USER_GUIDE.md").read_text(),"docs/USER_GUIDE.md","images/")]:
    refs=re.findall(r'src="([^"]+\.png)"',doc)
    assert len(refs)>=(7 if filename=="README.md" else 14),(filename,len(refs))
    for ref in refs:
        assert ref.startswith(prefix),(filename,ref)
        assert (root/filename).parent.joinpath(ref).is_file(),ref
assert "excel-export-dialog.png" not in readme
assert "excel-export-dialog.png" not in (root/"docs/USER_GUIDE.md").read_text()
print("V2_SCREENSHOT_GALLERY_QA_PASS",len(image_specs),"original verified PNGs")
