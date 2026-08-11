from pathlib import Path
from xml.etree import ElementTree as ET


TOOLS = Path(__file__).parents[1] / "tools" / "neutrons" / "powder_diffraction"


def _root(name: str) -> ET.Element:
    return ET.parse(TOOLS / name).getroot()


def _top_level_sections(root: ET.Element) -> list[str]:
    inputs = root.find("inputs")
    assert inputs is not None
    return [section.attrib["name"] for section in inputs.findall("section")]


def test_analyze_keeps_scientific_inputs_common_to_both_routes() -> None:
    root = _root("radar_pd_analyze.xml")

    assert _top_level_sections(root) == [
        "measurement",
        "library",
        "data_inputs",
        "chemistry",
        "pattern",
        "background",
        "magnetic",
        "safeguards",
        "analysis",
        "reproducibility",
    ]

    analysis = root.find("./inputs/section[@name='analysis']")
    assert analysis is not None
    mode = analysis.find("./conditional[@name='strategy']/param[@name='analysis_mode']")
    assert mode is not None
    assert mode.attrib.get("display") == "radio"
    selected = mode.find("./option[@selected='true']")
    assert selected is not None and selected.attrib.get("value") == "full"

    # Route-specific controls must not wrap measurement, data, or chemistry inputs.
    strategy = analysis.find("./conditional[@name='strategy']")
    assert strategy is not None
    assert strategy.find("./when[@value='full']/conditional[@name='full_profile']") is not None
    assert strategy.find("./when[@value='rapid']/section[@name='rapid_controls']") is not None


def test_analyze_diffraction_picker_excludes_non_pattern_artifacts() -> None:
    root = _root("radar_pd_analyze.xml")
    source = root.find(
        "./inputs/section[@name='data_inputs']/conditional[@name='input_source']"
        "/param[@name='source_kind']"
    )
    assert source is not None
    selected_source = source.find("./option[@selected='true']")
    assert selected_source is not None and selected_source.attrib.get("value") == "choose"

    data = root.find(
        "./inputs/section[@name='data_inputs']/conditional[@name='input_source']"
        "/when[@value='history']/param[@name='diffraction_pattern']"
    )
    assert data is not None
    accepted = {value.strip() for value in data.attrib["format"].split(",")}

    assert accepted == {"tabular", "xml"}
    assert accepted.isdisjoint({"data", "yaml", "json", "cif", "zip", "html"})
    data_validator = data.find("./validator[@type='expression']")
    assert data_validator is not None and ".xrdml" in (data_validator.text or "")

    instrument = root.find(
        "./inputs/section[@name='data_inputs']/conditional[@name='input_source']"
        "/when[@value='history']/conditional[@name='instrument_source']"
        "/when[@value='uploaded']/param[@name='instrument_file']"
    )
    assert instrument is not None and instrument.attrib.get("format") == "txt"
    instrument_validator = instrument.find("./validator[@type='expression']")
    assert instrument_validator is not None and ".instprm" in (instrument_validator.text or "")


def test_reusable_configuration_uses_the_same_route_contract() -> None:
    root = _root("radar_pd_configure.xml")

    assert _top_level_sections(root) == [
        "measurement",
        "chemistry",
        "pattern",
        "background",
        "magnetic",
        "safeguards",
        "analysis",
    ]

    analysis = root.find("./inputs/section[@name='analysis']")
    assert analysis is not None
    mode = analysis.find("./conditional[@name='strategy']/param[@name='analysis_mode']")
    assert mode is not None
    selected = mode.find("./option[@selected='true']")
    assert selected is not None and selected.attrib.get("value") == "full"
