#!/usr/bin/env python
"""Build production release artifact for ZIME.

Supported arguments:
  --clean   Clean previous build dirs before building.
  --test    Only validate paths and settings (no actual build).

Exit codes:
  0: ok
  1: validation or config error
  2: packager misconfiguration
  3: packager error during build
"""

import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build ZIME release")
    parser.add_argument("--clean", action="store_true", help="Clean build directories before building")
    parser.add_argument("--test", action="store_true", help="Validate only, no packager invocation")
    args = parser.parse_args()

    # Validate directories
    build_dir = PROJECT_ROOT / "build"
    dist_dir = PROJECT_ROOT / "dist"
    spec_file = PROJECT_ROOT / "zime.spec"
    assets_dir = PROJECT_ROOT / "assets"
    config_dir_src = PROJECT_ROOT / "config"
    if not os.path.isfile(config_dir_src / "desktop.json"):
        print("FAIL: config/desktop.json missing; cannot package")
        return 1

    if args.clean:
        for d in [build_dir, dist_dir]:
            if d.exists():
                shutil.rmtree(d)

    print("OK: directories validated")
    if args.test:
        print("--test passed")
        return 0

    # Check PyInstaller
    import PyInstaller.__main__
    print("OK: PyInstaller available")

    # Do the onefile build into dist (warnings are ok)
    cmd = [
        "--onefile",
        "--windowed",
        "--clean",
        "--name=zime",
        f"--specpath={build_dir}",
        f"--workpath={build_dir / 'work'}",
        f"--distpath={dist_dir}",
        f"--add-data={assets_dir}{os.pathsep}assets",
        f"--add-data={config_dir_src / 'desktop.json'}{os.pathsep}config",
        "--icon=assets/icons/zime.ico",
        "--specpath=.",
        str(PROJECT_ROOT / "launcher.py"),
    ]

    print("Running PyInstaller with:", " ".join(cmd))
    try:
        PyInstaller.__main__.run(cmd)
    except Exception as exc:
        print("FAIL: PyInstaller failed:", exc)
        return 2

    print("OK: PyInstaller finished")
    print("Release artifacts in:", dist_dir)
    return 0

if __name__ == "__main__":
    sys.exit(main())
