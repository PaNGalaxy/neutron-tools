import os
from pathlib import Path


# TODO: I'm skipping old tools that didn't have these checks as many prototype tools don't pass these checks.
# As tools are retired or moved out of prototype this list should trend to zero. :)
skip_tests = [
    "imaginex_subhkl_predict.xml",
    "nomad-montecarlo.xml",
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
