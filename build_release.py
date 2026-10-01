"""Build the complete source ZIP and VSIX using only the standard library."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = "1.9.17"
CORE = ("dad.py", "vnext.py", "ui.py", "aldad_syntax.py", "aldad_runtime.py")
IGNORE = {"__pycache__", ".pytest_cache", ".git", "build_exe", "dist_exe", "node_modules"}


def sources(folder):
    for p in sorted(folder.rglob("*")):
        if p.is_file() and not any(x in IGNORE for x in p.relative_to(folder).parts):
            if p.suffix not in (".pyc", ".pyo", ".vsix", ".zip"):
                yield p


def add(archive, file, name):
    info = zipfile.ZipInfo(str(name).replace("\\", "/"), (2026, 9, 30, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, file.read_bytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT.parent)
    opts = ap.parse_args()
    opts.output.mkdir(parents=True, exist_ok=True)
    extension = ROOT / "vscode" / "extension"
    package = json.loads((extension / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == "2.9.17" and VERSION in package["displayName"]
    ns = {"v": "http://schemas.microsoft.com/developer/vsx-schema/2011"}
    identity = ET.parse(ROOT/"vscode/extension.vsixmanifest").find("v:Metadata/v:Identity", ns)
    assert identity.get("Version") == package["version"]
    assert identity.get("Publisher") == package["publisher"] == "saud"
    for name in CORE:
        assert (ROOT/name).read_bytes() == (extension/name).read_bytes(), name
    vsix = opts.output / f"Aldad_VSCode_{VERSION}.vsix"
    with zipfile.ZipFile(vsix, "w") as z:
        for name in ("[Content_Types].xml", "extension.vsixmanifest"):
            add(z, ROOT/"vscode"/name, name)
        for file in sources(extension):
            add(z, file, "extension/" + file.relative_to(extension).as_posix())
    archive = opts.output / f"Aldad_{VERSION}_IDE_Pro.zip"
    prefix = f"Aldad_{VERSION}_IDE_Pro/"
    with zipfile.ZipFile(archive, "w") as z:
        for file in sources(ROOT):
            add(z, file, prefix + file.relative_to(ROOT).as_posix())
        add(z, vsix, prefix + vsix.name)
    for file in (vsix, archive):
        with zipfile.ZipFile(file) as z:
            assert z.testzip() is None
            count = len(z.infolist())
        print(json.dumps({"file": str(file), "bytes": file.stat().st_size,
                          "entries": count, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
