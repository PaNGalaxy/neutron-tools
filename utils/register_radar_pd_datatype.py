#!/usr/bin/env python3
"""Idempotently register custom binary crystallography/diffraction datatypes (GPX, MTZ)."""

from __future__ import annotations

import argparse
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


EXPECTED_EXTENSIONS = ("gpx", "mtz")


def _datatype_elements(fragment: Path) -> list[ET.Element]:
    root = ET.parse(fragment).getroot()
    elements = root.findall("./registration/datatype")
    if not elements:
        raise ValueError(f"Expected at least one datatype element in {fragment}")
    seen_ext: set[str] = set()
    for el in elements:
        ext = (el.attrib.get("extension") or "").strip()
        if not ext:
            raise ValueError(f"Datatype element missing 'extension' attribute in {fragment}")
        if ext in seen_ext:
            raise ValueError(f"Duplicate datatype extension {ext!r} in {fragment}")
        seen_ext.add(ext)
    for req_ext in EXPECTED_EXTENSIONS:
        if req_ext not in seen_ext:
            raise ValueError(f"Expected {req_ext!r} datatype in {fragment}")
    return elements


def register_datatype(config: Path, fragment: Path) -> bool:
    """Add any missing datatypes from *fragment* to *config* and return whether it changed."""
    datatypes = _datatype_elements(fragment)
    text = config.read_text(encoding="utf-8")
    ET.fromstring(text)

    missing: list[ET.Element] = []
    for dt in datatypes:
        ext = dt.attrib["extension"]
        pattern = rf'<datatype\b[^>]*\bextension=["\']{re.escape(ext)}["\']'
        if not re.search(pattern, text):
            missing.append(dt)

    if not missing:
        return False

    closing = re.search(r"^(?P<indent>[ \t]*)</registration>", text, re.MULTILINE)
    if closing is None:
        raise ValueError(f"No </registration> element found in {config}")

    indent = closing.group("indent") + "    "
    insert_lines = []
    for dt in missing:
        attributes = " ".join(f'{key}="{value}"' for key, value in dt.attrib.items())
        insert_lines.append(f"{indent}<datatype {attributes}/>\n")
    insertion = "".join(insert_lines)
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
    print(
        "Registered custom diffraction datatypes (gpx, mtz)."
        if changed
        else "Custom diffraction datatypes (gpx, mtz) are already registered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
