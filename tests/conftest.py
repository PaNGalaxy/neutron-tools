import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, List, Optional

import pytest

# The Kibana helpers are shared with the planemo reports, which are post-processed by
# scripts/add_kibana_links.py on the runner rather than under pytest.
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from kibana import SECTION_NAME, log_section  # noqa: E402


def pytest_generate_tests(metafunc) -> None:
    tool_paths = []
    interactive_tools = []
    folders_to_skip = ["retired"]
    for root, folders, files in os.walk("tools"):
        folders[:] = [folder for folder in folders if folder not in folders_to_skip]
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


class LogWindow:
    """Records when a test's Galaxy jobs were submitted, so a failure can link to their logs."""

    def __init__(self) -> None:
        self.start: Optional[float] = None
        self.job_ids: List[str] = []

    def job_submitted(self, job_id: Optional[str] = None) -> None:
        """Note that a job was just submitted.

        The first submission opens the window that the log link covers; later ones
        only add their job id to the report.
        """
        if self.start is None:
            self.start = time.time()
        if job_id and job_id not in self.job_ids:
            self.job_ids.append(job_id)


LOG_WINDOW_KEY = pytest.StashKey[LogWindow]()


@pytest.fixture(autouse=True)
def log_window(request: Any) -> LogWindow:
    """Window of time a failing test should show logs for."""
    window = LogWindow()
    request.node.stash[LOG_WINDOW_KEY] = window
    return window


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Any, call: Any) -> Any:
    """Attach a link to the logs of the window a failing test ran in."""
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    window = item.stash.get(LOG_WINDOW_KEY, None)
    start = window.start if window and window.start else call.start
    end = call.stop or time.time()

    section = log_section(start, end, window.job_ids if window else [])
    if not section:
        return

    # The section lands in the job log and the junit report through the longrepr
    if hasattr(report.longrepr, "addsection"):
        report.longrepr.addsection(SECTION_NAME, section)
    else:
        report.sections.append((SECTION_NAME, section))
