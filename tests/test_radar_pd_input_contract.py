import io
import json
import pickle
import sys
import types
from contextlib import redirect_stdout
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


def test_library_builder_carries_the_scientific_name_into_history_outputs() -> None:
    root = _root("radar_pd_library_builder.xml")

    library_name = root.find("./inputs/param[@name='library_name']")
    assert library_name is not None
    assert library_name.attrib.get("optional") is None
    assert library_name.attrib.get("value") == "custom_candidate_library"

    outputs = root.find("outputs")
    assert outputs is not None
    assert outputs.find("./data[@name='library_archive']").attrib["label"] == (
        "RADAR-PD portable custom library | ${library_name}.zip"
    )
    assert outputs.find("./data[@name='library_manifest']").attrib["label"] == (
        "RADAR-PD custom library manifest | ${library_name}.json"
    )


def test_monitor_profile_publishes_fit_plots_and_gpx_but_not_the_heavy_archive() -> None:
    root = _root("radar_pd_analyze.xml")
    outputs = root.find("outputs")
    assert outputs is not None

    plots = outputs.find("./collection[@name='plots']")
    assert plots is not None
    assert plots.find("filter") is None

    gpx_projects = outputs.find("./collection[@name='gpx_projects']")
    assert gpx_projects is not None
    assert gpx_projects.find("filter") is None

    archive = outputs.find("./data[@name='results_archive']")
    assert archive is not None
    assert (archive.findtext("filter") or "").strip() == "output_profile == 'full'"

    command = root.findtext("command", default="")
    publisher = root.findtext("./configfiles/configfile[@name='publish_plot_payloads']", default="")
    assert "python '$publish_plot_payloads' work/run portal" in command
    assert 'summary.get("artifacts", {}).get("plots", [])' in publisher
    assert '".plotdata_arrays.npz"' in publisher
    assert 'metadata["arrays_npz"] = arrays_destination.name' in publisher


def test_analyze_republishes_a_main_only_full_project_for_gsasii(tmp_path: Path, monkeypatch) -> None:
    root = _root("radar_pd_analyze.xml")
    command = root.findtext("command", default="")
    publisher = root.findtext(
        "./configfiles/configfile[@name='publish_gpx_fallback']",
        default="",
    )
    assert "python '$publish_gpx_fallback' work portal '$output_profile'" in command
    assert "tee -a '$console_output'" in command

    work = tmp_path / "work"
    run = work / "run" / "demo"
    project = run / "Technical" / "GSAS_Projects" / "demo_project.gpx"
    project.parent.mkdir(parents=True)
    project.write_bytes(b"GPX")
    portal = tmp_path / "portal"
    portal.mkdir()
    (portal / "summary.json").write_text(
        json.dumps(
            {
                "run_name": "demo",
                "analysis_mode": "full",
                "status": "complete",
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    fake_outputs = types.ModuleType("ndip_outputs")
    fake_outputs._publish_gpx = lambda path, root: False
    fake_outputs._published_name = lambda path, root, collection: path.name
    fake_outputs._gpx_stage = lambda relative: "refinement_checkpoint"
    fake_outputs.build_gpx_index = lambda *args, **kwargs: {
        "projects": [
            {
                "path": "Technical/GSAS_Projects/demo_project.gpx",
                "stage": "refinement_checkpoint",
                "status": "checkpoint",
            }
        ]
    }

    def collect_outputs(run_root, output_root, **kwargs):
        assert run_root == run.resolve()
        assert output_root == portal.resolve()
        assert fake_outputs._publish_gpx(project, run.resolve()) is True
        assert fake_outputs._published_name(project, run.resolve(), "gpx") == "02_Main_phase_anchor.gpx"
        assert fake_outputs._gpx_stage(project.relative_to(run).as_posix()) == "main_phase_anchor"
        index = fake_outputs.build_gpx_index(run)
        assert index["projects"][0]["stage"] == "main_phase_anchor"
        assert index["projects"][0]["status"] == "accepted"
        assert kwargs["include_archive"] is False

    fake_outputs.collect_outputs = collect_outputs
    monkeypatch.setitem(sys.modules, "ndip_outputs", fake_outputs)
    monkeypatch.setattr(
        sys,
        "argv",
        ["publish_gpx_fallback", str(work), str(portal), "monitor"],
    )

    exec(compile(publisher, "<publish_gpx_fallback>", "exec"), {})


def test_analyze_augmented_library_compatibility_entry_point(tmp_path: Path, monkeypatch) -> None:
    root = _root("radar_pd_analyze.xml")
    command = root.findtext("command", default="")
    wrapper = root.findtext(
        "./configfiles/configfile[@name='ndip_runner_compat']",
        default="",
    )
    assert "python '$ndip_runner_compat' analyze" in command

    pack_root = tmp_path / "custom_database" / "library"
    pack_root.mkdir(parents=True)
    (pack_root / "manifest.json").write_text(
        '{"kind":"augmented","source_type":"neutron"}',
        encoding="utf-8",
    )
    builtin_root = tmp_path / "database_neutron"
    builtin_root.mkdir()
    builtin_original = builtin_root / "highsymm_metadata.json"
    builtin_original.write_text("{}", encoding="utf-8")

    fake_runner = types.ModuleType("ndip_runner")

    def materialize(contract, **kwargs):
        return {
            "db": {
                "catalog_csv": str(kwargs["db_root"] / "catalog_deduplicated.csv"),
                "original_json": str(kwargs["db_root"] / "highsymm_metadata.json"),
            }
        }

    def fake_main():
        resolved = fake_runner._materialize_contract_config(
            {"analysis": {"radiation": "neutron"}},
            db_root=pack_root,
        )
        assert Path(resolved["db"]["original_json"]) == builtin_original.resolve()
        return 0

    fake_runner._materialize_contract_config = materialize
    fake_runner._db_root_for = lambda radiation, explicit: builtin_root
    fake_runner.main = fake_main
    monkeypatch.setitem(sys.modules, "ndip_runner", fake_runner)

    try:
        exec(compile(wrapper, "ndip_runner_compat", "exec"), {})
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("compatibility entry point did not invoke ndip_runner")


def test_monitor_plot_publisher_copies_interactive_sidecars(tmp_path: Path, monkeypatch) -> None:
    root = _root("radar_pd_analyze.xml")
    publisher = root.findtext("./configfiles/configfile[@name='publish_plot_payloads']", default="")
    run_root = tmp_path / "work" / "run"
    source = run_root / "rapid_results" / "live_run" / "curve.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"png")
    Path(str(source) + ".plotdata.json").write_text(
        json.dumps(
            {
                "plot_kind": "gsas_fit_with_ticks_v1",
                "source_plot": source.name,
                "arrays_npz": source.name + ".plotdata.npz",
            }
        ),
        encoding="utf-8",
    )
    Path(str(source) + ".plotdata.npz").write_bytes(b"npz")

    portal = tmp_path / "portal"
    published = portal / "plots" / "Rapid_final_fit.png"
    published.parent.mkdir(parents=True)
    published.write_bytes(b"png")
    (portal / "summary.json").write_text(
        json.dumps(
            {
                "artifacts": {
                    "plots": [
                        {
                            "source_path": "rapid_results/live_run/curve.png",
                            "path": "plots/Rapid_final_fit.png",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", ["publish_plot_payloads", str(run_root), str(portal)])
    exec(compile(publisher, "<publish_plot_payloads>", "exec"), {})

    metadata_path = Path(str(published) + ".plotdata.json")
    arrays_path = Path(str(published) + ".plotdata_arrays.npz")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["source_plot"] == published.name
    assert metadata["arrays_npz"] == arrays_path.name
    assert arrays_path.read_bytes() == b"npz"
    assert metadata_path.stem != arrays_path.stem


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


def test_gsasii_interactive_opens_a_copy_and_publishes_the_edited_gpx() -> None:
    root = _root("radar_pd_gsasii_interactive.xml")

    assert root.attrib.get("tool_type") == "interactive"
    assert root.attrib.get("profile") == "22.05"
    assert root.attrib.get("version") == "0.1.11"

    container = root.find("./requirements/container")
    assert container is not None
    assert (container.text or "").strip().endswith(
        ":gsasii-gui-e1d858113df4483bc0001832a0fc934f7925784e"
    )

    entrypoint = root.find("./entry_points/entry_point")
    assert entrypoint is not None
    assert entrypoint.attrib.get("label") == "gsasii"
    assert entrypoint.attrib.get("requires_path_in_url") == "True"
    assert entrypoint.findtext("port") == "8080"

    ep_path = root.find("./environment_variables/environment_variable[@name='EP_PATH']")
    assert ep_path is not None
    assert ep_path.attrib.get("inject") == "entry_point_path_for_label"
    assert (ep_path.text or "").strip() == "gsasii"

    source = root.find("./inputs/conditional[@name='project_source']")
    assert source is not None
    selector = source.find("./param[@name='source_kind']")
    assert selector is not None
    selected = selector.find("./option[@selected='true']")
    assert selected is not None and selected.attrib.get("value") == "collection"
    collection = source.find("./when[@value='collection']/param[@name='gpx_projects']")
    assert collection is not None and collection.attrib.get("format") == "gpx,binary"
    project = source.find("./when[@value='single']/param[@name='gpx_project']")
    assert project is not None and project.attrib.get("format") == "gpx,binary"
    validator = project.find("./validator[@type='expression']")
    assert validator is not None
    assert "accepted_model_after_pass_" in (validator.text or "")

    command = root.findtext("./command", default="")
    assert 'GSASII_SOURCE_PROJECT="\\$selected_project"' in command
    assert "GSASII_OUTPUT_PROJECT='$edited_project'" in command
    assert "GSASII_OUTPUT_ARCHIVE='$exported_files'" in command
    assert "python '$validate_project'" in command
    assert "/opt/gsasii-gui/start.sh" in command

    validator_script = root.findtext(
        "./configfiles/configfile[@name='validate_project']", default=""
    )
    assert "pickletools.genops" in validator_script

    selector_script = root.findtext(
        "./configfiles/configfile[@name='select_project']", default=""
    )
    assert "is_pickle_project" in selector_script
    assert "contains no valid GSAS-II GPX project" in selector_script

    edited = root.find("./outputs/data[@name='edited_project']")
    exported = root.find("./outputs/data[@name='exported_files']")
    log = root.find("./outputs/data[@name='session_log']")
    assert edited is not None and edited.attrib.get("format") == "binary"
    assert exported is not None and exported.attrib.get("format") == "zip"
    assert log is not None and log.attrib.get("format") == "txt"
    assert "${on_string}" in edited.attrib.get("label", "")
    assert "${on_string}" in exported.attrib.get("label", "")
    assert "${on_string}" in log.attrib.get("label", "")


def test_nova_interactive_uses_the_smoke_tested_release_image() -> None:
    root = _root("radar_pd_nova.xml")
    container = root.find("./requirements/container")

    assert root.attrib.get("version") == "0.3.91"
    assert container is not None
    assert container.text == (
        "ghcr.io/lalityadav07/impurity_detection_gsas_ver6:"
        "nova-bce7c4af2d22c546cf49fb8c93bacc71afd7f23e"
    )


def test_gsasii_collection_selector_skips_corrupt_higher_priority_checkpoint(
    tmp_path: Path, monkeypatch
) -> None:
    root = _root("radar_pd_gsasii_interactive.xml")
    selector = root.findtext(
        "./configfiles/configfile[@name='select_project']", default=""
    )
    valid = tmp_path / "Accepted_model_after_pass_2.gpx"
    with valid.open("wb") as handle:
        pickle.dump(["Controls", {}], handle, protocol=1)
    (tmp_path / "Accepted_model_after_pass_9.gpx").write_bytes(b"not a pickle")
    with (tmp_path / "02_main_phase_anchor.gpx").open("wb") as handle:
        pickle.dump(["Controls", {}], handle, protocol=1)

    monkeypatch.setattr(sys, "argv", ["select_project", str(tmp_path)])
    output = io.StringIO()
    with redirect_stdout(output):
        exec(compile(selector, "<select_project>", "exec"), {})

    assert Path(output.getvalue().strip()) == valid.resolve()
