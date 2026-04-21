import subprocess
import sys
from itertools import chain
from typing import Any, Dict, List

import pytest
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.parser.output_objects import ToolOutputCollection
from galaxy.util.template import fill_template


def _parse_inputs(input_sources: Any) -> Dict[str, Any]:
    if input_sources is None:
        return {}

    inputs: Dict[str, Any] = {}
    for source in chain.from_iterable(input_sources):
        try:
            key = source.parse_name()
        except Exception:
            continue

        nested_sources = [source.parse_nested_inputs_source().parse_input_sources()]
        conditional_sources = [
            conditional_source[1].parse_input_sources()
            for conditional_source in source.parse_when_input_sources()
        ]
        if nested_sources == [[]] and conditional_sources == []:
            inputs[key] = "__ndip_testing_value"
        if nested_sources != [[]]:
            if source.input_type == "repeat":
                inputs[key] = [_parse_inputs(nested_sources)]
            else:
                inputs[key] = _parse_inputs(nested_sources)
        if conditional_sources != []:
            if inputs[key] == "__ndip_testing_value":
                inputs[key] = _parse_inputs(conditional_sources)
            else:
                inputs[key] = inputs[key] | _parse_inputs(conditional_sources)

    return inputs


def _check_planemo_linter(xml_path: str) -> None:
    # Test with the planemo linter to validate common missing required parameters
    subprocess.run(
        [
            "planemo",
            "lint",
            "--fail_level=error",
            "--report_level=error",
            "--skip",
            "ValidDatatypes,XSD",
            xml_path,
        ],
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
    page_sources = tool_source.parse_input_pages().page_sources
    inputs = _parse_inputs([page.parse_input_sources() for page in page_sources])

    # Test if we can build a valid command from the cheetah template
    try:
        fill_template(
            command,
            inputs | dict.fromkeys(outputs, "test"),
            retry=0,
        )
    except Exception as exc:
        # These will get flagged but are expected for input files.
        if "'element_identifier'" not in str(exc) and "'name'" not in str(exc):
            raise


def _check_missing_output(xml_path: str) -> None:
    tool_source = get_tool_source(xml_path)

    # Parse tool command and outputs
    command = tool_source.parse_command()

    # Unlike in fill_template, we need to skip collections here
    output_items = tool_source.parse_outputs(None)[0]
    outputs: List[str] = []
    for key, value in output_items.items():
        if isinstance(value, ToolOutputCollection):
            continue
        outputs.append(key)

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
