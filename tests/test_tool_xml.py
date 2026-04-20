import subprocess
import sys
from itertools import chain

import pytest
from galaxy.tool_util.parser import get_tool_source
from galaxy.util.template import fill_template


def _check_planemo_linter(xml_path: str) -> None:
    # Test with the planemo linter to validate common missing required parameters
    subprocess.run(
        ["planemo", "lint", "--fail_level=error", "--report_level=error", xml_path],
        capture_output=True,
        check=True,
        text=True,
    )


def _check_tool_command(xml_path: str) -> None:
    tool_source = get_tool_source(xml_path)

    # Parse tool command and outputs
    command = tool_source.parse_command()
    outputs = tool_source.parse_outputs(None)[0].keys()

    # Parse tool inputs
    input_pages = tool_source.parse_input_pages()
    input_sources = [page.parse_input_sources() for page in input_pages.page_sources]
    inputs = [input.parse_name() for input in chain.from_iterable(input_sources)]

    # Test if we can build a valid command from the cheetah template
    fill_template(
        command, dict.fromkeys(inputs, 0) | dict.fromkeys(outputs, 0), retry=0
    )


def _check_missing_output(xml_path: str) -> None:
    tool_source = get_tool_source(xml_path)

    # Parse tool command and outputs
    command = tool_source.parse_command()
    outputs = tool_source.parse_outputs(None)[0].keys()

    for output in outputs:
        if f"${output}" not in command:
            raise ValueError(
                f"The tool command never references declared output '{output}'. This will cause your tool to behave unexpectedly in Galaxy."
            )


def test_tool_xml(xml_path) -> None:
    _check_planemo_linter(xml_path)
    _check_tool_command(xml_path)
    _check_missing_output(xml_path)


if __name__ == "__main__":
    pytest.main(sys.argv)
