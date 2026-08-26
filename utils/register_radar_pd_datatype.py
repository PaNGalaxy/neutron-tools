#!/usr/bin/env python3
"""Idempotently register RADAR-PD's opaque GSAS-II GPX datatype."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET


GPX_EXTENSION = "gpx"


def _datatype_element(fragment: Path) -> ET.Element:
    root = ET.parse(fragment).getroot()
    matches = root.findall(f"./registration/datatype[@extension='{GPX_EXTENSION}']")
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {GPX_EXTENSION!r} datatype in {fragment}")
    return matches[0]


def register_datatype(config: Path, fragment: Path) -> bool:
    """Add the GPX datatype to *config* and return whether it changed."""
    datatype = _datatype_element(fragment)
    text = config.read_text(encoding="utf-8")
    ET.fromstring(text)

    existing = re.search(r'<datatype\b[^>]*\bextension=["\']gpx["\']', text)
    if existing:
        return False

    closing = re.search(r"^(?P<indent>[ \t]*)</registration>", text, re.MULTILINE)
    if closing is None:
        raise ValueError(f"No </registration> element found in {config}")

    indent = closing.group("indent") + "    "
    attributes = " ".join(f'{key}="{value}"' for key, value in datatype.attrib.items())
    insertion = f"{indent}<datatype {attributes}/>\n"
    updated = text[: closing.start()] + insertion + text[closing.start() :]
    ET.fromstring(updated)

    mode = config.stat().st_mode
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=config.parent,
        prefix=f".{config.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(updated)
        temporary = Path(handle.name)
    try:
        os.chmod(temporary, mode)
        os.replace(temporary, config)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--fragment", type=Path, required=True)
    args = parser.parse_args()

    changed = register_datatype(args.config, args.fragment)
    print("Registered RADAR-PD gpx datatype." if changed else "RADAR-PD gpx datatype is already registered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
