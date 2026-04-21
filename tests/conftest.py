import os
from pathlib import Path


# TODO: I'm skipping old tools that didn't have these checks as many prototype tools don't pass these checks.
# As tools are retired or moved out of prototype this list should trend to zero. :)
skip_tests = [
    "analyzer.xml",
    "asrp_gsas2_refinement.xml",
    "data_assembler.xml",
    "gravitas_sunny.xml",
    "imaginex_analysis.xml",
    "imaginex_image_converter.xml",
    "imaginex_image_generator.xml",
    "imaginex_instrument_coverage.xml",
    "imaginex_merge.xml",
    "imaginex_occupancy.xml",
    "imaginex_subhkl.xml",
    "imaginex_subhkl_integrate.xml",
    "imaginex_subhkl_peak_fit.xml",
    "imaginex_subhkl_predict.xml",
    "imaginex_subhkl_prepare_peaks.xml",
    "Incident_beam_simulation_diffractometer.xml",
    "mlsans_fit_wlc.xml",
    "ml-test-chat.xml",
    "ml-test-infer.xml",
    "ml-test-load.xml",
    "ml-test-train.xml",
    "nexus_processor.xml",
    "nomad-montecarlo.xml",
    "pydebyer.xml",
    "reduction.xml",
    "sammy.xml",
    "sample-simulator.xml",
    "sample_simulator_diffraction.xml",
    "snap_incident_beam.xml",
]


def pytest_generate_tests(metafunc) -> None:
    tool_paths = []
    for root, _, files in os.walk("tools"):
        for name in files:
            if name in skip_tests:
                continue

            fname = os.path.join(root, name)
            path = Path(fname)
            if path.suffix == ".xml":
                tool_paths.append(str(path))

    metafunc.parametrize(
        "xml_path",
        tool_paths,
        ids=[os.path.basename(tool_path) for tool_path in tool_paths],
    )
