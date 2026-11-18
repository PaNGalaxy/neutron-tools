from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from utils.register_subhkl_datatype import register_datatype


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "tool_data" / "subhkl_datatypes_conf.xml.sample"


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
    matches = root.findall("./registration/datatype[@extension='mtz']")
    assert len(matches) == 1
    assert matches[0].attrib == {
        "extension": "mtz",
        "type": "galaxy.datatypes.binary:Binary",
        "mimetype": "application/octet-stream",
        "display_in_upload": "true",
    }


def test_register_datatype_preserves_existing_custom_datatypes(tmp_path: Path) -> None:
    config = tmp_path / "datatypes_conf.xml"
    config.write_text(
        '<?xml version="1.0"?>\n<datatypes>\n'
        '  <registration converters_path="converters" display_path="displays">\n'
        '    <datatype extension="gpx" type="galaxy.datatypes.binary:Binary" '
        'mimetype="application/octet-stream" display_in_upload="true"/>\n'
        "  </registration>\n</datatypes>\n",
        encoding="utf-8",
    )

    assert register_datatype(config, FRAGMENT) is True
    assert register_datatype(config, FRAGMENT) is False

    root = ET.parse(config).getroot()
    assert len(root.findall("./registration/datatype[@extension='gpx']")) == 1
    assert len(root.findall("./registration/datatype[@extension='mtz']")) == 1


def test_subhkl_and_careless_tools_accept_mtz_or_binary_uploads_and_emit_mtz() -> None:
    careless_root = ET.parse(
        ROOT / "tools" / "neutrons" / "imaginex_subhkl_merge.xml"
    ).getroot()
    refl_param = careless_root.find("./inputs/param[@name='reflections']")
    assert refl_param is not None
    assert refl_param.attrib.get("format") == "mtz,binary"
    for out_name in ("merged_mtz", "predictions_mtz", "xval_mtz"):
        out_el = careless_root.find(f"./outputs/data[@name='{out_name}']")
        assert out_el is not None
        assert out_el.attrib.get("format") == "mtz"

    cov_root = ET.parse(
        ROOT / "tools" / "neutrons" / "imaginex_instrument_coverage.xml"
    ).getroot()
    cov_in = cov_root.find("./inputs/param[@name='input']")
    assert cov_in is not None
    assert cov_in.attrib.get("format") == "mtz,binary"

    analysis_root = ET.parse(
        ROOT / "tools" / "neutrons" / "imaginex_analysis.xml"
    ).getroot()
    for param_name in ("coverage_file", "phasing_file", "honly_file", "file"):
        param_el = analysis_root.find(f".//param[@name='{param_name}']")
        assert param_el is not None
        assert param_el.attrib.get("format") == "mtz,binary"
