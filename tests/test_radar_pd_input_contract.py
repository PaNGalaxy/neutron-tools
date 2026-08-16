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


def test_analyze_diffraction_picker_accepts_all_hosted_app_formats() -> None:
    root = _root("radar_pd_analyze.xml")
    source = root.find(
        "./inputs/section[@name='data_inputs']/conditional[@name='input_source']"
        "/param[@name='source_kind']"
    )
    assert source is not None
    selected_source = source.find("./option[@selected='true']")
    assert selected_source is not None and selected_source.attrib.get("value") == "choose"
    history_option = source.find("./option[@value='history']")
    assert history_option is not None
    assert "Upload from laptop" in (history_option.text or "")

    data = root.find(
        "./inputs/section[@name='data_inputs']/conditional[@name='input_source']"
        "/when[@value='history']/param[@name='diffraction_pattern']"
    )
    assert data is not None
    accepted = {value.strip() for value in data.attrib["format"].split(",")}

    assert accepted == {"data", "tabular", "xml"}
    assert data.attrib.get("optional") is None
    assert "New upload Beta" in data.attrib.get("help", "")
    data_validator = data.find("./validator[@type='expression']")
    assert data_validator is not None
    validator_text = data_validator.text or ""
    for extension in (".dat", ".xye", ".gsa", ".gss", ".gsas", ".fxye", ".xrdml"):
        assert extension in validator_text

    instrument = root.find(
        "./inputs/section[@name='data_inputs']/conditional[@name='input_source']"
        "/when[@value='history']/conditional[@name='instrument_source']"
        "/when[@value='uploaded']/param[@name='instrument_file']"
    )
    assert instrument is not None and instrument.attrib.get("format") == "data,txt"
    assert instrument.attrib.get("optional") is None
    assert "New upload Beta" in instrument.attrib.get("help", "")
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


def test_analyze_outputs_start_with_native_overview_and_hide_report_internals() -> None:
    root = _root("radar_pd_analyze.xml")
    outputs = root.find("outputs")
    assert outputs is not None

    overview = outputs.find("./data[@name='overview']")
    assert overview is not None
    assert overview.attrib.get("format") == "tabular"
    assert overview.attrib.get("label") == "RADAR-PD 1 | Result overview"

    report = outputs.find("./data[@name='report']")
    summary = outputs.find("./data[@name='summary']")
    assert report is not None and report.attrib.get("hidden") == "true"
    assert summary is not None and summary.attrib.get("hidden") == "true"

    archive = outputs.find("./data[@name='results_archive']")
    assert archive is not None and archive.attrib.get("label") == "RADAR-PD 7 | Complete results archive"


def test_result_explorer_defaults_to_one_complete_archive() -> None:
    root = _root("radar_pd_result_explorer.xml")
    source = root.find("./inputs/conditional[@name='result_source']")
    assert source is not None
    selector = source.find("./param[@name='source_kind']")
    assert selector is not None
    selected = selector.find("./option[@selected='true']")
    assert selected is not None and selected.attrib.get("value") == "archive"
    archive = source.find("./when[@value='archive']/param[@name='results_archive']")
    assert archive is not None and archive.attrib.get("format") == "zip"

    entrypoint = root.find("./entry_points/entry_point")
    assert entrypoint is not None
    assert entrypoint.attrib.get("requires_path_in_url") == "True"

    entry_path = root.find("./environment_variables/environment_variable[@name='EP_PATH']")
    assert entry_path is not None
    assert entry_path.attrib.get("inject") == "entry_point_path_for_label"
    assert (entry_path.text or "").strip() == entrypoint.attrib.get("label")

    container = root.find("./requirements/container")
    assert container is not None
    assert (container.text or "").strip().endswith("radar-pd-nova:nova-0.3.2")

    command = root.findtext("./command", default="")
    assert "python -m zipfile -e" in command
    assert "python '$prepare_static_prefix'" in command
    assert "python -m http.server 8080" in command
    assert "$output" in command

    prefix_shim = root.findtext("./configfiles/configfile[@name='prepare_static_prefix']", default="")
    assert 'os.environ.get("EP_PATH", "")' in prefix_shim
    assert "link.symlink_to(root" in prefix_shim

    output = root.find("./outputs/data[@name='output']")
    assert output is not None and output.attrib.get("format") == "txt"
