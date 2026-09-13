"""Install the pinned golangci-lint release into tools/bin."""

from __future__ import annotations

import hashlib
import io
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.lint.constants import (  # noqa: E402
    GOLANGCI_RELEASE_TAG,
    GOLANGCI_VERSION,
    RELEASE_ASSET,
    RELEASE_SHA256,
)
from oba_revieweval.lint.runner import default_tools_bin, golangci_binary, read_golangci_version  # noqa: E402


def _platform_key() -> tuple[str, str]:
    import platform

    system = platform.system().lower()
    machine = platform.machine().lower()
    if system.startswith("win"):
        system = "windows"
    if machine in {"x86_64", "amd64"}:
        machine = "amd64"
    elif machine in {"aarch64", "arm64"}:
        machine = "arm64"
    return system, machine


def main() -> int:
    system, machine = _platform_key()
    asset = RELEASE_ASSET.get((system, machine))
    if not asset:
        print(f"unsupported platform {system}/{machine}", file=sys.stderr)
        return 2
    expected = RELEASE_SHA256[asset]
    url = (
        "https://github.com/golangci/golangci-lint/releases/download/"
        f"{GOLANGCI_RELEASE_TAG}/{asset}"
    )
    print(f"downloading {url}")
    with urlopen(url) as response:  # noqa: S310 - pinned GitHub release URL
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected:
        print(f"checksum mismatch: {digest} != {expected}", file=sys.stderr)
        return 2
    dest_dir = default_tools_bin()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = golangci_binary(dest_dir)
    if asset.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = [name for name in archive.namelist() if name.endswith("golangci-lint.exe")]
            if not names:
                print("zip missing golangci-lint.exe", file=sys.stderr)
                return 2
            dest.write_bytes(archive.read(names[0]))
    else:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            member = next(
                (item for item in archive.getmembers() if item.name.endswith("/golangci-lint")),
                None,
            )
            if member is None:
                print("tarball missing golangci-lint", file=sys.stderr)
                return 2
            extracted = archive.extractfile(member)
            if extracted is None:
                print("tarball member not a file", file=sys.stderr)
                return 2
            dest.write_bytes(extracted.read())
            dest.chmod(0o755)
    version = read_golangci_version(dest)
    if version != GOLANGCI_VERSION:
        print(f"installed {version}, expected {GOLANGCI_VERSION}", file=sys.stderr)
        return 2
    print(f"installed {dest} ({version}, sha256:{digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
