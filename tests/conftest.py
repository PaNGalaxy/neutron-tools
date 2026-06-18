import os
import xml.etree.ElementTree as ET
from pathlib import Path


def pytest_generate_tests(metafunc) -> None:
    tool_paths = []
    interactive_tools = []
    for root, _, files in os.walk("tools"):
        for name in files:
            fname = os.path.join(root, name)
            path = Path(fname)
            if path.suffix == ".xml":
                tool_paths.append(str(path))
                tree = ET.parse(path).getroot()
                if tree.attrib.get("tool_type", "") == "interactive":
                    interactive_tools.append(tree.attrib.get("id"))

    if "xml_path" in metafunc.fixturenames:
        metafunc.parametrize(
            "xml_path",
            tool_paths,
            ids=[os.path.basename(tool_path) for tool_path in tool_paths],
        )

    if "interactive_tool" in metafunc.fixturenames:
        metafunc.parametrize("interactive_tool", interactive_tools)
