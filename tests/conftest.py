import os
from pathlib import Path


def pytest_generate_tests(metafunc) -> None:
    if "xml_path" in metafunc.fixturenames:
        tool_paths = []
        for root, _, files in os.walk("tools"):
            for name in files:
                fname = os.path.join(root, name)
                path = Path(fname)
                if path.suffix == ".xml":
                    tool_paths.append(str(path))

        metafunc.parametrize(
            "xml_path",
            tool_paths,
            ids=[os.path.basename(tool_path) for tool_path in tool_paths],
        )
