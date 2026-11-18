from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from utils.register_radar_pd_datatype import register_datatype


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "tool_data" / "radar_pd_datatypes_conf.xml.sample"


def test_register_datatype_is_valid_and_idempotent(tmp_path: Path) -> None:
    config = tmp_path / "datatypes_conf.xml"
    config.write_text(
        '<?xml version="1.0"?>\n<datatypes>\n'
        '  <registration converters_path="converters" display_path="displays">\n'
        '    <datatype extension="txt" type="galaxy.datatypes.data:Text"/>\n'
        "  </registration>\n</datatypes>\n",
        encoding="utf-8",
    )

    assert register_datatype(config, FRAGMENT) is True
    assert register_datatype(config, FRAGMENT) is False

    root = ET.parse(config).getroot()
    matches = root.findall("./registration/datatype[@extension='gpx']")
    assert len(matches) == 1
    assert matches[0].attrib == {
        "extension": "gpx",
        "type": "galaxy.datatypes.binary:Binary",
        "mimetype": "application/octet-stream",
        "display_in_upload": "true",
    }


def test_analyze_publishes_gpx_collection_with_binary_compatibility() -> None:
    root = ET.parse(
        ROOT / "tools" / "neutrons" / "powder_diffraction" / "radar_pd_analyze.xml"
    ).getroot()
    collection = root.find("./outputs/collection[@name='gpx_projects']")
    assert collection is not None
    assert collection.attrib.get("format") == "binary"
    discovery = collection.find("./discover_datasets")
    assert discovery is not None
    assert discovery.attrib.get("ext") == "binary"
