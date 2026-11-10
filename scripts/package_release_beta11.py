"""Create, validate and checksum complete jwDaily Hydration Log beta.11 installation ZIP."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

VERSION = "1.1.0-beta.11"
BASENAME = "20261110 jwDaily Hydration Log v1.1.0-beta.11.zip"
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "dist" / BASENAME
CUSTOM = ROOT / "custom_components" / "jw_daily_hydration_log"
OTHERS = (
    "README.md", "CHANGELOG.md", "hacs.json",
    "LICENSE", "LICENSE-UPSTREAM-MIT",
    "RELEASE_NOTES_v1.1.0-beta.11.md",
    "examples/apexcharts-jwdhl-v1.1.0-beta.11.md",
)

def main():
    assert CUSTOM.is_dir(), "integration source directory missing"
    assert json.loads((CUSTOM / "manifest.json").read_text())["version"] == VERSION
    files = [p for p in CUSTOM.rglob("*")
             if p.is_file() and not any(part in ("__pycache__", ".git") for part in p.parts)
             and p.suffix not in (".pyc", ".pyo")]
    files += [ROOT / name for name in OTHERS if (ROOT / name).is_file()]
    files.sort(key=lambda p: p.relative_to(ROOT).as_posix())
    assert len(files) >= 12, len(files)
    assert all(p.is_relative_to(ROOT) and p.stat().st_size > 0 for p in files)
    TARGET.parent.mkdir(exist_ok=True)
    assert not TARGET.exists(), "Do not overwrite an existing release package"
    names = set()
    with zipfile.ZipFile(TARGET, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=8) as z:
        for p in files:
            name = p.relative_to(ROOT).as_posix()
            assert not name.startswith("/") and ".." not in Path(name).parts and name not in names
            names.add(name)
            info = zipfile.ZipInfo(name, date_time=(2026,11,10,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=8)
    with zipfile.ZipFile(TARGET, "r") as z:
        assert z.testzip() is None, "ZIP CRC failure"
        assert set(z.namelist()) == names, "ZIP file list mismatch"
        assert all(x.file_size > 0 for x in z.infolist())
        manifest = json.loads(z.read("custom_components/jw_daily_hydration_log/manifest.json"))
        card = z.read("custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js")
        const = z.read("custom_components/jw_daily_hydration_log/const.py")
        excel = z.read("custom_components/jw_daily_hydration_log/excel.py")
        assert manifest["version"] == VERSION
        assert b"v1.1.0-beta.11" in card and b"VERSION = '1.1.0-beta.11'" in const and b"VERSION = '1.1.0-beta.11'" in excel
        assert b"background:#B3E5FC" in card
        assert b"background:#EEEEEE" in card
        assert b"background:#FFFFFF" in card
        assert b"Undo last drink" not in card
        assert b"drink moments" in card
    digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    sidecar = TARGET.with_suffix(".sha256")
    assert not sidecar.exists(), "Do not overwrite a checksum from another run"
    sidecar.write_text(f"{digest}  {BASENAME}\n", encoding="utf-8")
    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == digest
    print("FILE_QA_PASS", BASENAME, "size", TARGET.stat().st_size, "files",len(names), "SHA-256", digest, "ZIP CRC PASS")
    print("RELEASE_ZIP_PATH", TARGET)

if __name__ == "__main__":
    main()
